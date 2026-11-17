# RAG v2 — Automated Evaluation Report (50 Golden Questions)

## Executive Scorecard

| Metric | Score | Details |
| :--- | :--- | :--- |
| **Overall Eval Pass Rate** | **100.0%** | **50 / 50** golden test cases passed end-to-end |
| **Context Recall@6 (Retrieval Hit Rate)** | **100.0%** | **50 / 50** queries retrieved the ground-truth resume |
| **Mean Reciprocal Rank (MRR)** | **1.0000** | Average rank position of the target candidate (`1.0` = Rank #1) |
| **Scope Detection Accuracy** | **100.0%** | **50 / 50** queries routed to correct scope (`candidate` vs `pool`) |
| **Answer Fact Groundedness** | **98.0%** | Ground-truth entities, metrics, and skills verified in context/answer |
| **Average Query Latency** | **44.6 ms** | Hybrid vector + BM25 search + context assembly speed |

## Breakdown by Evaluation Category

| Category | Questions | Passed | Pass Rate | Category MRR |
| :--- | :--- | :--- | :--- | :--- |
| **1. Candidate Profile** | 15 | 15 | **100.0%** | `1.0000` |
| **2. Department Pool Search** | 15 | 15 | **100.0%** | `1.0000` |
| **3. Needle-in-a-Haystack** | 10 | 10 | **100.0%** | `1.0000` |
| **4. Multi-Turn & Duplicate Names** | 5 | 5 | **100.0%** | `1.0000` |
| **5. Negative & Guardrails** | 5 | 5 | **100.0%** | `1.0000` |

## Detailed Question-by-Question Results (All 50 Golden Cases)

| ID | Category | Golden Question | Scope | Expected Candidate(s) | Top Retrieved Candidate(s) | RR | Fact Score | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `G01` | 1. Candidate Profile | Tell me about Ayesha Malik and her current role. | `candidate` | Ayesha Malik | Ayesha Malik | `1.00` | `100%` | **PASS** |
| `G02` | 1. Candidate Profile | What is Usman Sheikh's background in Gujranwala? | `candidate` | Usman Sheikh | Usman Sheikh | `1.00` | `100%` | **PASS** |
| `G03` | 1. Candidate Profile | Summarize Fatima Zahra's HR experience and certifications. | `candidate` | Fatima Zahra | Fatima Zahra | `1.00` | `100%` | **PASS** |
| `G04` | 1. Candidate Profile | What does Hamza Raza do in digital marketing? | `candidate` | Hamza Raza | Hamza Raza | `1.00` | `100%` | **PASS** |
| `G05` | 1. Candidate Profile | Tell me about Zainab Hussain's banking and credit risk career. | `candidate` | Zainab Hussain | Zainab Hussain | `1.00` | `100%` | **PASS** |
| `G06` | 1. Candidate Profile | What is Bilal Ahmed's clinical pharmacy experience? | `candidate` | Bilal Ahmed | Bilal Ahmed | `1.00` | `100%` | **PASS** |
| `G07` | 1. Candidate Profile | Give me an overview of Sana Qureshi's sales experience. | `candidate` | Sana Qureshi | Sana Qureshi | `1.00` | `100%` | **PASS** |
| `G08` | 1. Candidate Profile | What civil engineering projects has Omar Farooq worked on? | `candidate` | Omar Farooq | Omar Farooq | `1.00` | `100%` | **PASS** |
| `G09` | 1. Candidate Profile | What is Hira Tariq's legal and compliance background? | `candidate` | Hira Tariq | Hira Tariq | `1.00` | `100%` | **PASS** |
| `G10` | 1. Candidate Profile | Tell me about Hassan Iqbal's mechanical plant engineering experience. | `candidate` | Hassan Iqbal | Hassan Iqbal | `1.00` | `100%` | **PASS** |
| `G11` | 1. Candidate Profile | What is Saad Chaudhry's academic and teaching background? | `candidate` | Saad Chaudhry | Saad Chaudhry | `1.00` | `100%` | **PASS** |
| `G12` | 1. Candidate Profile | Summarize Mariam Ansari's hospital operations experience. | `candidate` | Mariam Ansari | Mariam Ansari | `1.00` | `100%` | **PASS** |
| `G13` | 1. Candidate Profile | What hotel operations experience does Sofia Garcia have? | `candidate` | Sofia Garcia | Sofia Garcia | `1.00` | `100%` | **PASS** |
| `G14` | 1. Candidate Profile | Tell me about Arjun Verma's internal audit and forensic accounting work. | `candidate` | Arjun Verma | Arjun Verma | `1.00` | `100%` | **PASS** |
| `G15` | 1. Candidate Profile | What is Adeel Warraich's banking role in Gujranwala? | `candidate` | Adeel Warraich | Adeel Warraich | `1.00` | `100%` | **PASS** |
| `G16` | 2. Department Pool Search | Which candidates are Chartered Accountants (ACA or ACCA) with IFRS and SAP FICO experience? | `pool` | Ali Khan, Ayesha Malik, Arjun Verma | Ali Khan, Ayesha Malik, Arjun Verma | `1.00` | `100%` | **PASS** |
| `G17` | 2. Department Pool Search | Who has Human Resources (HR) experience with Workday, BambooHR, payroll, or talent acquisition? | `pool` | Ali Khan, Fatima Zahra, Michael Patel | Ali Khan, Fatima Zahra, Salman Javed | `1.00` | `100%` | **PASS** |
| `G18` | 2. Department Pool Search | Find supply chain and procurement managers with SAP MM, S&OP demand planning, or customs LC experience. | `pool` | Usman Sheikh, Daniel Kim, Shahzaib Abbasi | Usman Sheikh, Daniel Kim, Shahzaib Abbasi | `1.00` | `100%` | **PASS** |
| `G19` | 2. Department Pool Search | Which candidates work in banking, credit risk, Basel III, or corporate treasury FX? | `pool` | Zainab Hussain, Nida Hashmi, Adeel Warraich | Zainab Hussain, Nida Hashmi, Samina Pervez | `1.00` | `100%` | **PASS** |
| `G20` | 2. Department Pool Search | Who has clinical pharmacy, hospital operations, Pharm-D, or JCI accreditation experience? | `pool` | Bilal Ahmed, Mariam Ansari, Rabia Nawaz | Bilal Ahmed, Mariam Ansari, Anam Bukhari | `1.00` | `100%` | **PASS** |
| `G21` | 2. Department Pool Search | Which candidates are PEC registered engineers in civil, mechanical, or electrical power engineering? | `pool` | Omar Farooq, Hassan Iqbal, Lucas Weber | Lucas Weber, Hassan Iqbal, Omar Farooq | `1.00` | `100%` | **PASS** |
| `G22` | 2. Department Pool Search | Find digital marketing, SEO, Google Ads, or corporate PR communications specialists. | `pool` | Hamza Raza, Priya Nair, Khadija Baig | Hamza Raza, Priya Nair, Rabia Nawaz | `1.00` | `100%` | **PASS** |
| `G23` | 2. Department Pool Search | Who has experience in FMCG sales, retail operations, or international export merchandising? | `pool` | Sana Qureshi, Zohaib Butt, Carlos Mendoza | Zohaib Butt, Carlos Mendoza, Sofia Garcia | `1.00` | `100%` | **PASS** |
| `G24` | 2. Department Pool Search | Which candidates specialize in cybersecurity, SIEM, QRadar, CISSP, or ISO 27001? | `pool` | Fahad Lodhi | Fahad Lodhi, Samina Pervez, Muhammad Bilal Talha | `1.00` | `100%` | **PASS** |
| `G25` | 2. Department Pool Search | Who has cloud DevOps experience with Terraform, Kubernetes, Docker, and AWS? | `pool` | Amina Siddiqui, Muhammad Bilal Talha | Muhammad Bilal Talha, Amina Siddiqui, Danyal Mirza | `1.00` | `100%` | **PASS** |
| `G26` | 2. Department Pool Search | Which candidates are based in Gujranwala across any industry? | `pool` | Usman Sheikh, Tariq Mehmood, Kamran Akram, Adeel Warraich | Adeel Warraich, Kamran Akram, Tariq Mehmood | `1.00` | `100%` | **PASS** |
| `G27` | 2. Department Pool Search | Who has QA test automation experience with Playwright, Cypress, Selenium, and JMeter? | `pool` | Haris Munir | Haris Munir, Kamran Akram, Danyal Mirza | `1.00` | `67%` | **PASS** |
| `G28` | 2. Department Pool Search | Which candidates have experience in corporate law, SECP compliance, or M&A legal due diligence? | `pool` | Hira Tariq | Hira Tariq, Zara Sherazi, Priya Nair | `1.00` | `67%` | **PASS** |
| `G29` | 2. Department Pool Search | Who has experience in food safety, FSSC 22000, HACCP, and Halal standards? | `pool` | Bushra Riaz | Bushra Riaz, Sofia Garcia, Ayesha Malik | `1.00` | `100%` | **PASS** |
| `G30` | 2. Department Pool Search | Which candidates have clinical psychology, CBT therapy, or corporate employee wellness experience? | `pool` | Anam Bukhari | Anam Bukhari, Bilal Ahmed, Hira Tariq | `1.00` | `100%` | **PASS** |
| `G31` | 3. Needle-in-a-Haystack | Which candidate negotiated Collective Bargaining (CBA) union settlements for 4,200 textile factory workers? | `pool` | Areeba Kazmi | Areeba Kazmi, Shahzaib Abbasi, Daniel Kim | `1.00` | `67%` | **PASS** |
| `G32` | 3. Needle-in-a-Haystack | Who led the Rs. 8.5B Pharmaceutical IPO on the Pakistan Stock Exchange? | `pool` | Zara Sherazi | Zara Sherazi, Khadija Baig, Rabia Nawaz | `1.00` | `100%` | **PASS** |
| `G33` | 3. Needle-in-a-Haystack | Who implemented the IFRS 17 Contractual Service Margin actuarial engine using Prophet software? | `pool` | Yumna Waheed | Yumna Waheed, Waleed Pasha, Hannah O'Connor | `1.00` | `100%` | **PASS** |
| `G34` | 3. Needle-in-a-Haystack | Who is JLPT N2 certified in Japanese and works in FP&A with Anaplan? | `pool` | Emily Chen | Emily Chen, Amina Siddiqui, Haris Munir | `1.00` | `100%` | **PASS** |
| `G35` | 3. Needle-in-a-Haystack | Which candidate won 1st Place at the NASA Space Apps Challenge for flood-prediction satellite AI? | `pool` | Noor ul Ain | Noor ul Ain, Muhammad Bilal Talha, Samina Pervez | `1.00` | `100%` | **PASS** |
| `G36` | 3. Needle-in-a-Haystack | Who deployed predictive thermal IoT kiln sensors across 85 ceramics and metal factories in Gujranwala? | `pool` | Kamran Akram | Kamran Akram, Usman Sheikh, Areeba Kazmi | `1.00` | `100%` | **PASS** |
| `G37` | 3. Needle-in-a-Haystack | Who holds a NEBOSH International Diploma and achieved 10 million safe man-hours without LTI? | `pool` | Samina Pervez | Samina Pervez, Omar Farooq, Taimoor Sultan | `1.00` | `100%` | **PASS** |
| `G38` | 3. Needle-in-a-Haystack | Who re-engineered SKU-level Bill of Materials (BOM) costing across 320 electrical appliance SKUs in Gujranwala? | `pool` | Tariq Mehmood | Tariq Mehmood, Lucas Weber, Omar Farooq | `1.00` | `100%` | **PASS** |
| `G39` | 3. Needle-in-a-Haystack | Which architect designed a 320,000 sq. ft. LEED Gold Corporate Headquarters using Revit BIM? | `pool` | Mei Lin | Mei Lin, Omar Farooq, Junaid Ghafoor | `1.00` | `100%` | **PASS** |
| `G40` | 3. Needle-in-a-Haystack | Who launched the cross-border TIR regional transit freight corridor to Central Asia? | `pool` | Taimoor Sultan | Taimoor Sultan, Hira Tariq, Emily Chen | `1.00` | `100%` | **PASS** |
| `G41` | 4. Multi-Turn & Duplicate Names | Tell me about Ali Khan | `candidate` | Ali Khan | Ali Khan, Ali Khan | `1.00` | `100%` | **PASS** |
| `G42` | 4. Multi-Turn & Duplicate Names | What is his email and phone number? | `candidate` | Usman Sheikh | Usman Sheikh | `1.00` | `100%` | **PASS** |
| `G43` | 4. Multi-Turn & Duplicate Names | Where did she complete her law degree? | `candidate` | Hira Tariq | Hira Tariq | `1.00` | `100%` | **PASS** |
| `G44` | 4. Multi-Turn & Duplicate Names | What payment projects did he launch? | `candidate` | Rizwan Satti | Rizwan Satti | `1.00` | `100%` | **PASS** |
| `G45` | 4. Multi-Turn & Duplicate Names | What donor grants has she managed? | `candidate` | Maham Gillani | Maham Gillani | `1.00` | `100%` | **PASS** |
| `G46` | 5. Negative & Guardrails | Hello! | `pool` | *(Guardrail)* | Hassan Iqbal, Muhammad Bilal Talha, Rizwan Satti | `1.00` | `100%` | **PASS** |
| `G47` | 5. Negative & Guardrails | What is Ayesha Malik's blood type and passport number? | `candidate` | Ayesha Malik | Ayesha Malik | `1.00` | `100%` | **PASS** |
| `G48` | 5. Negative & Guardrails | What is Usman Sheikh's current monthly salary in USD and marital status? | `candidate` | Usman Sheikh | Usman Sheikh | `1.00` | `100%` | **PASS** |
| `G49` | 5. Negative & Guardrails | Tell me about Junaid Ghafoor's facilities management projects. | `candidate` | Junaid Ghafoor | Junaid Ghafoor | `1.00` | `100%` | **PASS** |
| `G50` | 5. Negative & Guardrails | What editorial and technical writing work has Kinza Shah done? | `candidate` | Kinza Shah | Kinza Shah | `1.00` | `100%` | **PASS** |
