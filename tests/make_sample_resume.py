"""Creates a FICTIONAL sample resume PDF for demos and screenshots.

Run it with:  python -m tests.make_sample_resume
The person in this resume does not exist.
"""

from pathlib import Path

import pymupdf

OUTPUT = Path("sample_data/sample_resume.pdf")

CSS = """
h1 { color: #1f4e79; font-size: 20pt; }
h2 { color: #1f4e79; font-size: 12pt; margin-top: 12pt; }
p, li { font-size: 10pt; }
"""

HTML = """
<h1>ALEX MORGAN</h1>
<p>Bengaluru, India | alex.morgan@example.com</p>

<h2>PROFESSIONAL PROFILE</h2>
<p>Computer Applications graduate with hands-on academic project experience in data
cleaning, SQL analysis and dashboard building. Looking for an entry-level data
analyst role.</p>

<h2>EDUCATION</h2>
<ul>
<li>Master of Computer Applications (MCA), Sample University, expected 2027</li>
<li>Bachelor of Computer Applications (BCA), Sample College, 2022 - 2025</li>
</ul>

<h2>TECHNICAL SKILLS</h2>
<ul>
<li>SQL (MySQL), Microsoft Excel (pivot tables, lookups), Power BI (DAX basics)</li>
<li>Python (basic data cleaning)</li>
<li>Communication, attention to detail, problem solving</li>
</ul>

<h2>PROJECTS</h2>
<p><b>Sales Dashboard (Excel, SQL, Power BI)</b></p>
<ul>
<li>Cleaned a sample retail dataset and wrote SQL queries to summarize sales by region and category.</li>
<li>Built an interactive Power BI dashboard with KPI cards to show trends and top products.</li>
</ul>

<p><b>Customer Churn Analysis (SQL, Power BI)</b></p>
<ul>
<li>Explored customer records to find groups with higher churn.</li>
<li>Presented findings in a short dashboard for non-technical readers.</li>
</ul>
"""


def main():
    story = pymupdf.Story(html=HTML, user_css=CSS)
    writer = pymupdf.DocumentWriter(str(OUTPUT))
    page_rect = pymupdf.paper_rect("a4")
    text_area = page_rect + (50, 50, -50, -50)

    more_pages = True
    while more_pages:
        device = writer.begin_page(page_rect)
        more_pages, _ = story.place(text_area)
        story.draw(device)
        writer.end_page()
    writer.close()
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()