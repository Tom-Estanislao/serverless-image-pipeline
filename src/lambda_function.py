import io
import logging
import boto3
from PIL import Image

# Bucket where the thumbnails are saved
RESIZED_BUCKET = "capstone-resized-images-tom"

# Largest width or height of the thumbnail, in pixels
THUMBNAIL_SIZE = 128

# Logger that writes to CloudWatch; INFO level shows successes and errors
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Created outside the handler so warm runs reuse the same S3 connection
s3 = boto3.client("s3")


def lambda_handler(event, context):
    try:
        # Bucket and file name sent in by Step Functions
        bucket = event["bucket"]
        key = event["key"]

        # Download the original image into memory
        original = s3.get_object(Bucket=bucket, Key=key)["Body"].read()

        # Open it with Pillow and remember its format (JPEG, PNG, etc.) for saving
        img = Image.open(io.BytesIO(original))
        image_format = img.format

        # Shrink it in place; thumbnail() keeps the original shape
        img.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))

        # Save the thumbnail into memory in the same format
        buffer = io.BytesIO()
        img.save(buffer, format=image_format)

        # Upload it to the resized bucket under a thumbnails/ folder
        thumbnail_key = f"thumbnails/{key}"
        s3.put_object(
            Bucket=RESIZED_BUCKET,
            Key=thumbnail_key,
            Body=buffer.getvalue(),
            ContentType=Image.MIME[image_format],  # lets the browser show it instead of downloading it
        )

        # Log success so it shows in CloudWatch
        logger.info(f"Resized {bucket}/{key} to {RESIZED_BUCKET}/{thumbnail_key} ({img.width}x{img.height})")

        # The Choice state checks this "status" field
        return {"status": "SUCCESS", "thumbnailKey": thumbnail_key}

    except Exception as e:
        # Log the error so the cause shows in CloudWatch
        logger.error(f"Failed to resize {event.get('key')}: {e}")

        # Return FAILED instead of crashing so the Choice state can send it to the Fail state
        return {"status": "FAILED", "error": str(e)}