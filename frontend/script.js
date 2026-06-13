const uploadBtn = document.getElementById("uploadBtn");
const imageInput = document.getElementById("imageInput");
const resultsList = document.getElementById("resultsList");

// Lambda endpoints
const PRESIGNED_URL_ENDPOINT = "https://s1q286q66k.execute-api.ap-south-1.amazonaws.com/getPresignedUrl";
const FETCH_LABELS_ENDPOINT = "https://s1q286q66k.execute-api.ap-south-1.amazonaws.com/getLabels";

uploadBtn.addEventListener("click", () => {
  const file = imageInput.files[0];
  if (!file) {
    alert("Please select an image first!");
    return;
  }

  resultsList.innerHTML = "<li>Analyzing image...</li>";

  const reader = new FileReader();
  reader.onload = async () => {
    try {
      // Show preview
      document.getElementById("preview").src = reader.result;
      document.getElementById("preview").style.display = "block";

      // --- Get presigned URL ---
      const presignedRes = await fetch(`${PRESIGNED_URL_ENDPOINT}?fileType=${encodeURIComponent(file.type)}`);
      if (!presignedRes.ok) throw new Error("Failed to get presigned URL");
      const presignedData = await presignedRes.json();

      const uploadUrl = presignedData.uploadUrl;
      const imageKey = presignedData.key;

      // Upload to S3
      const uploadRes = await fetch(uploadUrl, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
        mode: "cors"
      });
      if (!uploadRes.ok) throw new Error(`S3 upload failed: ${uploadRes.status}`);

      // --- Retry fetching labels from DynamoDB ---
      const maxRetries = 15;      // slightly higher to allow Lambda processing
      const retryDelay = 1500;    // 1.5 seconds
      let labelsData = null;

      for (let i = 0; i < maxRetries; i++) {
        const labelsRes = await fetch(`${FETCH_LABELS_ENDPOINT}?key=${encodeURIComponent(imageKey)}`);
        if (labelsRes.ok) {
          labelsData = await labelsRes.json();
          break;  // exit loop once data is available
        } else if (labelsRes.status === 404) {
          resultsList.innerHTML = `<li>Processing image, please wait... (attempt ${i + 1}/${maxRetries})</li>`;
          await new Promise(r => setTimeout(r, retryDelay));
        } else {
          throw new Error(`getLabels request failed: ${labelsRes.status}`);
        }
      }

      if (!labelsData) {
        resultsList.innerHTML = "<li>Could not fetch labels. Please try again later.</li>";
        return; // stop execution
      }

      console.log("Labels fetched:", labelsData.Labels);

      // Display results with professional card-style look
resultsList.innerHTML = "";
if (labelsData.Labels && labelsData.Labels.length > 0) {
  labelsData.Labels.forEach(label => {
    const li = document.createElement("li");
    li.innerHTML = `
      <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 14px;
        background: rgba(0,255,255,0.05);
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,255,255,0.2);
        margin-bottom: 10px;
        transition: transform 0.2s, box-shadow 0.2s;
      ">
        <span style="font-weight:600; font-size:16px;">${label.Name}</span>
        <span style="font-weight:500; font-size:14px;">${label.Confidence.toFixed(2)}%</span>
      </div>
      <div style="
        background: #222;
        border-radius: 8px;
        height: 10px;
        overflow: hidden;
        margin-top:6px;
      ">
        <div style="
          width: ${label.Confidence}%;
          height: 100%;
          background: linear-gradient(90deg,#00ffcc,#0077ff);
          transition: width 0.6s ease;
        "></div>
      </div>
    `;
    resultsList.appendChild(li);
  });
} else {
  resultsList.innerHTML = "<li style='color:#fff;'>No labels detected.</li>";
}


      // Scroll results into view safely
      const resultsDiv = document.getElementById("results");
      if (resultsDiv) {
        resultsDiv.scrollIntoView({ behavior: "smooth", block: "start" });
      }

    } catch (error) {
      console.error(error);
      resultsList.innerHTML = "<li>Error analyzing image.</li>";
    }
  };

  reader.readAsDataURL(file);
});
