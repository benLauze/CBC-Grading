import argparse
import json
from PIL import Image

from gemini_grader import grade_card_with_gemini


def run_test(image_path):
    print(f"\nLoading image: {image_path}")

    image = Image.open(image_path)

    result = grade_card_with_gemini(image)

    print("\n=== Grading Result ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test Gemini Pokémon card grader"
    )

    parser.add_argument(
        "--image",
        required=True,
        help="Path to image file"
    )

    args = parser.parse_args()

    run_test(args.image)