"""Generate N synthetic resumes (PDF / DOCX / TXT) for load-testing the pipelines.  Usage: python make_sample_resumes.py OUTDIR [N]"""
import random
import sys
from pathlib import Path

FIRST = ["Muhammad", "Ali", "Sara", "Ayesha", "Omar", "Fatima", "Hamza", "Zainab", "Usman", "Hira", "Bilal", "Noor",
         "John", "Emily", "Michael", "Priya", "Chen", "Lucia", "Daniel", "Aisha", "Kevin", "Maria", "Tariq", "Sana"]
LAST = ["Khan", "Ahmed", "Malik", "Sheikh", "Butt", "Raza", "Iqbal", "Hussain", "Smith", "Johnson", "Patel", "Wang",
        "Garcia", "Brown", "Ansari", "Qureshi", "Chaudhry", "Siddiqui", "Mirza", "Baig"]
ROLES = {
    "backend": ("Backend Engineer", ["Python", "Django", "PostgreSQL", "Redis", "Docker", "REST APIs"]),
    "frontend": ("Frontend Developer", ["React", "TypeScript", "Tailwind CSS", "Next.js", "Jest", "Figma"]),
    "devops": ("DevOps Engineer", ["AWS", "Terraform", "Kubernetes", "Docker", "CI/CD", "Linux", "Ansible"]),
    "data": ("Data Scientist", ["Python", "Pandas", "scikit-learn", "SQL", "TensorFlow", "Tableau"]),
    "mobile": ("Mobile Developer", ["Flutter", "Dart", "Kotlin", "Swift", "Firebase"]),
    "fullstack": ("Full Stack Developer", ["Node.js", "React", "MongoDB", "Express", "AWS", "Docker"]),
}
COMPANIES = ["Techlogix", "Systems Ltd", "Arbisoft", "Netsol", "10Pearls", "Folio3", "Careem", "Daraz", "Afiniti", "Contour Software"]
CITIES = ["Lahore", "Karachi", "Islamabad", "Gujranwala", "Faisalabad", "Dubai", "London", "Toronto"]
UNIS = ["University of the Punjab", "NUST", "FAST-NUCES", "LUMS", "COMSATS University", "UET Lahore"]


def build(i, rng):
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    key = rng.choice(list(ROLES))
    title, skills = ROLES[key]
    city = rng.choice(CITIES)
    email = name.lower().replace(" ", ".") + f"{i}@example.com"
    y = 2026
    jobs, start = [], rng.randint(2015, 2020)
    for _ in range(rng.randint(2, 3)):
        end = start + rng.randint(1, 3)
        co = rng.choice(COMPANIES)
        jobs.append((f"{title}", co, f"{rng.choice(['Jan','Mar','Jun','Sep'])} {start}", "Present" if end >= y - 1 else f"Dec {end}",
                     [f"Built and maintained services using {rng.choice(skills)} and {rng.choice(skills)}, serving {rng.randint(10, 900)}k users.",
                      f"Reduced deployment time by {rng.randint(20, 70)}% by introducing {rng.choice(skills)} automation.",
                      f"Mentored {rng.randint(2, 6)} junior engineers and led code reviews."]))
        start = end
    jobs.reverse()
    lines = [name, f"{title} | {city}", f"{email} | +92 3{rng.randint(0,4)}{rng.randint(10,99)} {rng.randint(1000000,9999999)} | linkedin.com/in/{name.lower().replace(' ', '-')}",
             "SUMMARY", f"{title} with {y - int(jobs[-1][2].split()[1])} years of experience in {', '.join(skills[:3])}. Based in {city}.",
             "EXPERIENCE"]
    for t, co, s, e, bl in jobs:
        lines.append(f"{t} | {co} {s} – {e}")
        lines += [f"• {b}" for b in bl]
    lines += ["EDUCATION", f"BS Computer Science | {rng.choice(UNIS)} 2011 – 2015 | CGPA {rng.uniform(2.8, 3.9):.2f}",
              "SKILLS", f"Technical: {', '.join(skills)}", "Practices: Agile, Code Review, TDD",
              "PROJECTS", f"Inventory Tracker | {skills[0]}, {skills[1]} 2022 – 2023", f"• Built an inventory system used by {rng.randint(3, 40)} stores.",
              "CERTIFICATIONS", rng.choice(["AWS Certified Solutions Architect", "Google Cloud Associate", "Certified Kubernetes Administrator", "Scrum Master (PSM I)"])]
    return name, lines


def write_pdf(path, lines):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=A4)
    y = 800
    for ln in lines:
        c.setFont("Helvetica-Bold" if ln.isupper() or ln == lines[0] else "Helvetica", 11)
        c.drawString(40, y, ln.replace("–", "-").replace("•", "\u2022"))
        y -= 15
        if y < 50:
            c.showPage(); y = 800
    c.save()


def write_docx(path, lines):
    import docx
    d = docx.Document()
    for ln in lines:
        d.add_paragraph(ln)
    d.save(str(path))


def main(out, n=45, seed=7):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    for i in range(n):
        name, lines = build(i, rng)
        stem = name.replace(" ", "_") + f"_{i}"
        kind = rng.choices(["pdf", "docx", "txt"], [6, 3, 1])[0]
        p = out / f"{stem}_Resume.{kind}"
        {"pdf": write_pdf, "docx": write_docx, "txt": lambda p, l: p.write_text("\n".join(l), encoding="utf-8")}[kind](p, lines)
    print(f"wrote {n} resumes to {out}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 45)
