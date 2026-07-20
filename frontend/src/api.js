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

  const res = await fetch("http://10.220.80.237:8000/process-card", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error("Backend error");
  }

  return await res.json();
}
