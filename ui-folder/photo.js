import AWS from "aws-sdk";

const s3 = new AWS.S3({
  endpoint: "https://<SPACE_NAME>.<REGION>.digitaloceanspaces.com",
  accessKeyId: "<YOUR_ACCESS_KEY>",
  secretAccessKey: "<YOUR_SECRET_KEY>",
});

async function uploadToSpace(fileBuffer, fileName, contentType) {
  const params = {
    Bucket: "<SPACE_NAME>",  // your Space name
    Key: fileName,           // e.g., "review-123/photo.jpg"
    Body: fileBuffer,
    ACL: "public-read",      // so it can be accessed via URL
    ContentType: contentType
  };

  const result = await s3.upload(params).promise();
  return result.Location; // this is the public URL of the uploaded image
}

import express from "express";
import multer from "multer";

const app = express();
const upload = multer(); // in-memory storage

app.post("/reviews/:reviewId/photo", upload.single("photo"), async (req, res) => {
  try {
    const { reviewId } = req.params;
    const fileBuffer = req.file.buffer;
    const fileName = `review-${reviewId}-${Date.now()}.jpg`;
    
    // Upload to DigitalOcean Space
    const url = await uploadToSpace(fileBuffer, fileName, req.file.mimetype);

    // Save the URL to your database table
    await db.query(
      "INSERT INTO review_images (review_id, image_url) VALUES (?, ?)",
      [reviewId, url]
    );

    res.json({ success: true, url });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to upload image" });
  }
});

app.listen(3000, () => console.log("Server running on port 3000"));