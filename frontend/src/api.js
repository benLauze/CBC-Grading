export async function processCard(frontImageUri, backImageUri) {
  const formData = new FormData();

  formData.append("front", {
    uri: frontImageUri,
    name: "front.jpg",
    type: "image/jpeg",
  });

  formData.append("back", {
    uri: backImageUri,
    name: "back.jpg",
    type: "image/jpeg",
  });

  const API_URL = process.env.EXPO_PUBLIC_API_URL;

  const res = await fetch(`${API_URL}/process-card`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error("Backend error");
  }

  return await res.json();
}