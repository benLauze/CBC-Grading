"""
Train the image encoder used by the card-identification pipeline.

The model converts each card image into a 256-value embedding that can be
compared against stored card embeddings later. During training, two different
augmented versions of the same card are treated as a matching pair, while the
other cards in the batch act as non-matches.

Because the dataset mainly contains clean card images, the training pipeline
adds lighting changes, glare, blur, noise, and compression to better represent
phone photos. Claude helped with parts of the augmentation design, contrastive
training setup, and retrieval evaluation.

The best model is saved to Models/encoder_best.keras.
"""

import os
import csv
import random
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


# Training and model configuration
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
MANIFEST_PATH = PROJECT_DIR / "Reference" / "reference_manifest.csv"
MODELS_DIR = PROJECT_DIR / "Models"
CHECKPOINT_PATH = MODELS_DIR / "encoder_best.keras"

# TensorFlow automatically uses an available GPU.
IMAGE_SIZE = 224
EMBEDDING_DIM = 256
BATCH_SIZE = 32
EPOCHS = 12
LEARNING_RATE = 1e-4
TEMPERATURE = 0.07
VAL_FRACTION = 0.1
SEED = 42

# Freeze the pretrained ResNet backbone for faster testing, or leave it
# unfrozen to fine-tune the full model.
FREEZE_BACKBONE = False

random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)
AUTOTUNE = tf.data.AUTOTUNE


# Manifest path handling
# Rebuild stored Windows or Linux paths from the current project directory.
def resolve_image_path(raw_path):
    raw_path = str(raw_path).replace("\\", "/")
    parts = raw_path.split("/")
    for anchor in ("Card_Dataset", "Reference"):
        if anchor in parts:
            idx = parts.index(anchor)
            return str(PROJECT_DIR.joinpath(*parts[idx:]))
    return raw_path


# Load the manifest and create a card-level train/validation split
def load_manifest():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}")
    with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Use one local dataset image as the clean source for each card.
    rows = [r for r in rows if r.get("dataset_image_path")]
    return rows


def split_by_card(rows, val_fraction):
    unique_ids = sorted({r["card_id"] for r in rows})
    random.shuffle(unique_ids)
    n_val = max(1, int(len(unique_ids) * val_fraction))
    val_ids = set(unique_ids[:n_val])
    train_rows = [r for r in rows if r["card_id"] not in val_ids]
    val_rows = [r for r in rows if r["card_id"] in val_ids]
    return train_rows, val_rows


# Image loading and ResNet preprocessing
def _read_image(path):
    data = tf.io.read_file(path)
    img = tf.image.decode_image(data, channels=3, expand_animations=False)
    img = tf.image.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
    return img / 255.0


def _preprocess(img01):
    """Apply the preprocessing expected by ResNet50."""
    return keras.applications.resnet50.preprocess_input(img01 * 255.0)


# Phone-photo augmentation helpers
def _box_blur(img, size=5):
    kernel = tf.ones((size, size, 3, 1)) / float(size * size)
    return tf.nn.depthwise_conv2d(img[None], kernel, [1, 1, 1, 1], "SAME")[0]


def _add_glare(img, cx, cy, radius, intensity):
    """Add a circular bright spot to imitate glare on a card surface."""
    xx, yy = tf.meshgrid(tf.range(IMAGE_SIZE, dtype=tf.float32),
                         tf.range(IMAGE_SIZE, dtype=tf.float32))
    dist = tf.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    glare = tf.clip_by_value(1.0 - dist / radius, 0.0, 1.0)[..., None]
    return img + glare * intensity


def _augment_train(img):
    """Create a strongly altered training view of a clean card image."""
    img = tf.image.random_brightness(img, max_delta=0.35)
    img = tf.image.random_contrast(img, 0.6, 1.4)
    img = tf.image.random_saturation(img, 0.6, 1.4)
    img = tf.image.random_hue(img, 0.08)

    # Claude-assisted glare simulation with random position, size, and strength.
    def glare_branch():
        cx = tf.random.uniform([], 0, IMAGE_SIZE)
        cy = tf.random.uniform([], 0, IMAGE_SIZE)
        radius = tf.random.uniform([], IMAGE_SIZE * 0.15, IMAGE_SIZE * 0.45)
        intensity = tf.random.uniform([], 0.25, 0.7)
        return _add_glare(img, cx, cy, radius, intensity)
    img = tf.cond(tf.random.uniform([]) < 0.4, glare_branch, lambda: img)

    # Random blur represents focus and movement problems in phone photos.
    img = tf.cond(tf.random.uniform([]) < 0.4, lambda: _box_blur(img, 5), lambda: img)

    # Add occasional sensor noise.
    img = tf.cond(tf.random.uniform([]) < 0.3,
                  lambda: img + tf.random.normal(tf.shape(img), 0.0, 0.03),
                  lambda: img)

    img = tf.clip_by_value(img, 0.0, 1.0)

    # Add occasional JPEG compression artifacts.
    def jpeg_branch():
        u = tf.cast(img * 255.0, tf.uint8)
        u = tf.image.random_jpeg_quality(u, 30, 75)
        return tf.cast(u, tf.float32) / 255.0
    img = tf.cond(tf.random.uniform([]) < 0.3, jpeg_branch, lambda: img)

    return tf.clip_by_value(img, 0.0, 1.0)


def _augment_eval(img):
    """Create the same moderate phone-photo degradation for every evaluation."""
    img = img * 0.82                                   # lower brightness
    img = (img - 0.5) * 1.15 + 0.5                     # increase contrast
    img = _box_blur(img, 5)                            # add mild blur
    img = _add_glare(img, IMAGE_SIZE * 0.35, IMAGE_SIZE * 0.3,
                     IMAGE_SIZE * 0.35, 0.45)          # add fixed glare
    return tf.clip_by_value(img, 0.0, 1.0)


# TensorFlow training and evaluation datasets
def make_train_dataset(rows):
    """Create two independently augmented views of each training card."""
    paths = [resolve_image_path(r["dataset_image_path"]) for r in rows]
    ds = tf.data.Dataset.from_tensor_slices(paths)
    ds = ds.shuffle(min(len(rows), 4096), seed=SEED, reshuffle_each_iteration=True)

    def _map(path):
        base = _read_image(path)
        view1 = _preprocess(_augment_train(base))
        view2 = _preprocess(_augment_train(base))
        return view1, view2

    ds = ds.map(_map, num_parallel_calls=AUTOTUNE)
    ds = ds.batch(BATCH_SIZE, drop_remainder=True).prefetch(AUTOTUNE)
    return ds


def make_index_dataset(rows):
    """Create the clean reference side of retrieval evaluation."""
    paths = [resolve_image_path(r["dataset_image_path"]) for r in rows]
    ds = tf.data.Dataset.from_tensor_slices(paths)
    ds = ds.map(lambda p: _preprocess(_read_image(p)), num_parallel_calls=AUTOTUNE)
    return ds.batch(BATCH_SIZE).prefetch(AUTOTUNE)


def make_query_dataset(rows):
    """Create the degraded query side of retrieval evaluation."""
    paths = [resolve_image_path(r["dataset_image_path"]) for r in rows]
    ds = tf.data.Dataset.from_tensor_slices(paths)
    ds = ds.map(lambda p: _preprocess(_augment_eval(_read_image(p))),
                num_parallel_calls=AUTOTUNE)
    return ds.batch(BATCH_SIZE).prefetch(AUTOTUNE)


# ResNet50 encoder and embedding layers
def build_encoder(freeze_backbone=False):
    backbone = keras.applications.ResNet50(
        include_top=False, weights="imagenet",
        input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3), pooling="avg")
    backbone.trainable = not freeze_backbone

    inputs = keras.Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3))
    features = backbone(inputs, training=not freeze_backbone)
    x = layers.Dense(512, activation="relu")(features)
    x = layers.Dense(EMBEDDING_DIM)(x)
    outputs = layers.UnitNormalization(axis=1)(x)   # normalize for cosine similarity
    return keras.Model(inputs, outputs, name="card_encoder")


# Contrastive training loss
# Claude helped with the NT-Xent setup that treats the matching augmented view
# as the positive example and the remaining batch items as negatives.
def nt_xent_loss(z1, z2, temperature=TEMPERATURE):
    batch = tf.shape(z1)[0]
    z = tf.concat([z1, z2], axis=0)
    sim = tf.matmul(z, z, transpose_b=True) / temperature
    sim = sim + tf.eye(2 * batch) * -1e9
    targets = tf.concat([tf.range(batch) + batch, tf.range(batch)], axis=0)
    return tf.reduce_mean(
        keras.losses.sparse_categorical_crossentropy(targets, sim, from_logits=True))


# Retrieval evaluation
# Claude helped create both an easier validation-only comparison and a harder
# full-index comparison against every card, which is closer to actual use.
def _embed_rows(model, rows, degraded):
    ds = make_query_dataset(rows) if degraded else make_index_dataset(rows)
    return model.predict(ds, verbose=0)


def _retrieval_metrics(query_embs, index_embs, correct_col):
    """Calculate retrieval accuracy, ranking, and similarity separation."""
    sims = np.matmul(query_embs, index_embs.T)          # query-to-index similarities
    order = np.argsort(-sims, axis=1)                    # best matches first
    n = sims.shape[0]

    top1 = float(np.mean(order[:, 0] == correct_col))
    top5 = float(np.mean(np.any(order[:, :5] == correct_col[:, None], axis=1)))

    # Find the position of the correct card in each ranked result.
    ranks = np.argmax(order == correct_col[:, None], axis=1) + 1
    mean_rank = float(np.mean(ranks))

    # Compare the correct-card similarity against the average incorrect match.
    pos_sim = sims[np.arange(n), correct_col]
    neg_mask = np.ones_like(sims, dtype=bool)
    neg_mask[np.arange(n), correct_col] = False
    neg_sim = sims[neg_mask].reshape(n, -1).mean(axis=1)
    gap = float(np.mean(pos_sim - neg_sim))
    return top1, top5, mean_rank, gap


def evaluate(model, val_rows, all_rows):
    """Evaluate degraded validation queries against small and full clean indexes."""
    q = _embed_rows(model, val_rows, degraded=True)     # simulated phone-photo queries

    # Easier test: compare validation queries only against validation cards.
    idx_val = _embed_rows(model, val_rows, degraded=False)
    correct_val = np.arange(len(val_rows))
    m_val = _retrieval_metrics(q, idx_val, correct_val)

    # Harder test: compare validation queries against every available card.
    idx_full = _embed_rows(model, all_rows, degraded=False)
    id_to_pos = {r["card_id"]: i for i, r in enumerate(all_rows)}
    correct_full = np.array([id_to_pos[r["card_id"]] for r in val_rows])
    m_full = _retrieval_metrics(q, idx_full, correct_full)

    return m_val, m_full


# Validation loss
# Use augmented validation pairs to compare training progress and overfitting.
def validation_loss(model, val_rows, max_batches=20):
    # Keep the last partial batch so smaller validation sets still produce a loss.
    paths = [resolve_image_path(r["dataset_image_path"]) for r in val_rows]
    ds = tf.data.Dataset.from_tensor_slices(paths)
    def _m(p):
        base = _read_image(p)
        return _preprocess(_augment_train(base)), _preprocess(_augment_train(base))
    ds = ds.map(_m, num_parallel_calls=AUTOTUNE).batch(BATCH_SIZE).prefetch(AUTOTUNE)
    total, count = 0.0, 0
    for v1, v2 in ds:
        if tf.shape(v1)[0] < 2:
            continue  # contrastive loss requires at least two cards
        z1 = model(v1, training=False)
        z2 = model(v2, training=False)
        total += float(nt_xent_loss(z1, z2))
        count += 1
        if count >= max_batches:
            break
    return total / max(1, count)


# Train, evaluate, and save the best encoder
def main():
    gpus = tf.config.list_physical_devices("GPU")
    print(f"TensorFlow device: {'GPU' if gpus else 'CPU'}  |  freeze_backbone={FREEZE_BACKBONE}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_manifest()
    print(f"Manifest rows (cards): {len(rows)}")
    train_rows, val_rows = split_by_card(rows, VAL_FRACTION)
    print(f"Train cards: {len(train_rows)}  |  Val cards: {len(val_rows)}")

    train_ds = make_train_dataset(train_rows)
    steps_per_epoch = len(train_rows) // BATCH_SIZE

    model = build_encoder(freeze_backbone=FREEZE_BACKBONE)
    optimizer = keras.optimizers.Adam(learning_rate=LEARNING_RATE)

    @tf.function
    def train_step(v1, v2):
        with tf.GradientTape() as tape:
            z1 = model(v1, training=True)
            z2 = model(v2, training=True)
            loss = nt_xent_loss(z1, z2)
        grads = tape.gradient(loss, model.trainable_variables)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))
        return loss

    best_top1 = -1.0
    for epoch in range(1, EPOCHS + 1):
        progbar = keras.utils.Progbar(steps_per_epoch, stateful_metrics=["loss"])
        running = 0.0
        step = 0
        for v1, v2 in train_ds:
            step += 1
            loss = train_step(v1, v2)
            running += float(loss)
            progbar.update(step, values=[("loss", running / step)])
            if step >= steps_per_epoch:
                break

        train_loss = running / max(1, step)
        val_loss = validation_loss(model, val_rows)
        m_val, m_full = evaluate(model, val_rows, rows)
        v_r1, v_r5, v_rank, v_gap = m_val
        f_r1, f_r5, f_rank, f_gap = m_full

        print("")
        print(f"Epoch {epoch:02d}/{EPOCHS}   train loss {train_loss:.3f}   val loss {val_loss:.3f}")
        print(f"   Easy test (vs {len(val_rows)} held-out cards):   "
              f"correct #1: {v_r1*100:.1f}%   in top 5: {v_r5*100:.1f}%")
        print(f"   Real test (vs all {len(rows)} cards):        "
              f"correct #1: {f_r1*100:.1f}%   in top 5: {f_r5*100:.1f}%")

        # Save the model with the best full-index Recall@1 because it measures
        # whether the correct card ranks first against the complete collection.
        if f_r1 > best_top1:
            best_top1 = f_r1
            model.save(CHECKPOINT_PATH)
            print(f"  saved new best -> {CHECKPOINT_PATH} (full-index R@1={f_r1:.3f})")

    print(f"\nDone. Best full-index Recall@1: {best_top1:.3f}")
    print(f"Best model: {CHECKPOINT_PATH}")


if __name__ == "__main__":
    main()