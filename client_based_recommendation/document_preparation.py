##################### prepare the document for processing #####################
import pandas as pd
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# 1. Read Excel file into DataFrame
df = pd.read_csv("../cognium_codebase/data/CRM_Meeting_Notes__preview_.csv")

# 2. Convert rows to JSON-like object (list of dicts)
data_json = df.to_dict(orient="records")

# 3. Save JSON to file (optional)
with open("data.json", "w") as f:
    json.dump(data_json, f, indent=4)

# 4. Create PDF from JSON
styles = getSampleStyleSheet()
doc = SimpleDocTemplate("output.pdf")

story = []

for row in data_json:
    for key, value in row.items():
        story.append(Paragraph(f"<b>{key}</b>: {value}", styles["Normal"]))
    story.append(Spacer(1, 12))  # Space between rows

doc.build(story)