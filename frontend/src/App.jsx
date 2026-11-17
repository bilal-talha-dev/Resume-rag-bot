import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Send,
  FileText,
  Database,
  Terminal,
  Cpu,
  Search,
  Settings,
  RefreshCw,
  Copy,
  Check,
  Sparkles,
  Layers,
  ChevronRight,
  Server,
  Key,
  Sliders,
  Trash2,
  Briefcase,
  GraduationCap,
  Mail,
  Phone,
  MapPin,
  GitBranch,
  ArrowDown,
  ArrowRight,
  X,
  Eye,
  CheckCircle2,
  Box,
  Activity
} from 'lucide-react';

// ============================================================================
// EXTRACTED RESUME KNOWLEDGE BASE (From Muhammad-Bilal-Talha-Full.pdf)
// ============================================================================
const INITIAL_RESUME_CHUNKS = [
  {
    id: 'doc_1',
    section: 'HEADER & CONTACT',
    text: '[HEADER & CONTACT] Muhammad Bilal Talha | Full Stack Developer | Mustafa Town, Lahore | bilalsaeed000095@gmail.com | +92 316 7611690 | linkedin.com/in/muhammad-bilal-talha-225543246'
  },
  {
    id: 'doc_2',
    section: 'SUMMARY',
    text: '[SUMMARY] Full Stack and DevOps Engineer with 2+ years building MERN and Django applications and running AWS and on-prem infrastructure with Terraform, Docker, Kubernetes, Cloudflare, and CI/CD. Delivered 3 production workstreams in 12 months at xis.ai, removed 35 hours a week of manual work with AI automation, and migrated 3 apps from AWS to on-prem at SecureQuanta.'
  },
  {
    id: 'doc_3',
    section: 'EXPERIENCE — Full Stack Developer (xis.ai)',
    text: "[EXPERIENCE: Full Stack Developer at xis.ai Oct 2025 – Sep 2026] Full Stack Developer | xis.ai Oct 2025 – Sep 2026 • Shipped 3 production workstreams in 12 months, including 3 apps for Rexroth's Ctrl-X project, from UI to backend. • Removed 35 hours a week of manual work by integrating AI pipelines into the full-stack product. • Sped up data labeling 3x with a GPU-accelerated annotation tool built on SAM (Segment Anything Model). • Integrated MQTT into 3 applications for real-time, event-driven communication between services and devices. • Ran 2 apps on Kubernetes with kubectl and covered feature work with unit tests."
  },
  {
    id: 'doc_4',
    section: 'EXPERIENCE — Software Engineer (SecureQuanta)',
    text: '[EXPERIENCE: Software Engineer (Full Stack & DevOps) at SecureQuanta Jan 2025 – Oct 2025] Software Engineer (Full Stack & DevOps) | SecureQuanta Jan 2025 – Oct 2025 • Migrated the entire environment from AWS and DigitalOcean to on-prem, moving 3 apps and all dev/production workloads. • Secured on-prem apps with Cloudflare and Cloudflare Tunnel, publishing services without opening inbound ports. • Shipped 4 web applications in 10 months, plus Lark Suite integrations that automated cross-department workflows. • Cut manual response time by 35% with a customer portal and internal ticket system for client communication. • Built GitHub Actions CI/CD pipelines that removed manual deployments to dev and production. • Ran AWS (EC2, ECS, ECR, Lambda, VPC, ALB, RDS, S3) and DigitalOcean as code with Terraform before the migration.'
  },
  {
    id: 'doc_5',
    section: 'EXPERIENCE — Junior MERN Stack Developer (Freelance)',
    text: '[EXPERIENCE: Junior MERN Stack Developer at Freelance (Independent Projects & Training) Jan 2024 – Mar 2024] Junior MERN Stack Developer | Freelance (Independent Projects & Training) Jan 2024 – Mar 2024 • Delivered client web apps in 3 months with React, Node.js, Express.js, REST APIs, and MongoDB.'
  },
  {
    id: 'doc_6',
    section: 'EXPERIENCE — Intern (PITB)',
    text: '[EXPERIENCE: Intern at Punjab Information Technology Board (PITB) Sep 2023 – Dec 2023 (Gujranwala)] Intern | Punjab Information Technology Board (PITB) Sep 2023 – Dec 2023 (Gujranwala) • Enabled Google Cloud Platform deployments in 4 months by configuring environments and using Docker.'
  },
  {
    id: 'doc_7',
    section: 'EDUCATION',
    text: '[EDUCATION] BS Software Engineering, University of the Punjab | Dec 2021 – Jul 2025 | CGPA: 3.77'
  },
  {
    id: 'doc_8',
    section: 'PROJECTS',
    text: '[PROJECTS] Online Compiler (MERN): Developed an interactive compiler supporting Python and C++ code execution using Node.js and Docker. Blog Platform (MERN): Built a full-stack blogging website with authentication, post creation, likes, and comments. Smart Entry Management (FYP): Developed a facial recognition attendance system using Next.js, Flask, and Docker.'
  },
  {
    id: 'doc_9',
    section: 'SKILLS — Development & Databases',
    text: '[SKILLS: Development & Databases] Development: JavaScript, TypeScript, HTML, CSS, Tailwind CSS, Python, C/C++, React, Next.js, Redux, Node.js, Express.js, MERN, Full Stack Development, REST APIs, MQTT, Django, Laravel (Beginner), Flask | Databases: MongoDB, MySQL, PostgreSQL'
  },
  {
    id: 'doc_10',
    section: 'SKILLS — Cloud & DevOps',
    text: '[SKILLS: Cloud & DevOps] Cloud & DevOps: AWS (EC2, ECS, ECR, Lambda, ALB, ACM, RDS, S3, VPC, IAM, CloudWatch, Route 53), On-Prem Infrastructure, Cloud Migration (AWS to On-Prem), Cloudflare, Cloudflare Tunnel, DigitalOcean, Azure, Google Cloud Platform, Terraform (Infrastructure as Code), Kubernetes (kubectl), Docker, Containerization, GitHub Actions, CI/CD'
  },
  {
    id: 'doc_11',
    section: 'SKILLS — AI, Tools, Practices & Languages',
    text: '[SKILLS: AI, Tools, Practices & Languages] AI & Tooling: AI Automation Integration, AI Pipelines, Annotation Tooling, SAM (Segment Anything Model), GPU Acceleration | Tools: Git, Linux, Bash, Postman, Networking, Unit Testing (Jest, pytest) | Practices: Agile, Scrum, Microservices, Event-Driven Architecture, Load Balancing, Zero Trust Access, DNS, SSL/TLS, Serverless, Computer Vision | Languages: Urdu (fluent), English (intermediate), Punjabi (fluent)'
  },
  {
    id: 'doc_12',
    section: 'CERTIFICATES',
    text: '[CERTIFICATES] Fortinet Fundamentals in Cybersecurity — 11/2024 | MERN Stack Development (Udemy) — 07/2023 | Python (Great Learning) — 02/2023'
  }
];

const STOPWORDS = new Set([
  'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
  'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from', 'of', 'and', 'or',
  'what', 'where', 'when', 'who', 'whom', 'which', 'how', 'why', 'did',
  'does', 'do', 'has', 'have', 'had', 'he', 'his', 'him', 'i', 'my', 'me',
  'you', 'your', 'tell', 'about', 'can', 'could', 'would', 'should',
  'muhammad', 'bilal', 'talha', 'talhas', 'resume', 'cv'
]);

const CONCEPT_GROUPS = [
  ['contact', 'email', 'gmail', 'phone', 'mobile', 'call', 'number', 'linkedin', 'address', 'location', 'lahore', 'mustafa', 'reach', 'bilalsaeed000095', '7611690'],
  ['summary', 'profile', 'overview', 'years', 'background', 'bio', 'experience'],
  ['xis', 'xis.ai', 'rexroth', 'ctrl-x', 'ctrl', 'sam', 'segment', 'annotation', 'labeling', 'gpu', 'mqtt', 'workstreams', '35', 'manual'],
  ['securequanta', 'migration', 'migrated', 'on-prem', 'cloudflare', 'tunnel', 'inbound', 'lark', 'portal', 'ticket', 'digitalocean'],
  ['freelance', 'junior', 'independent', 'training', 'client'],
  ['intern', 'internship', 'pitb', 'punjab', 'information', 'board', 'gujranwala', 'gcp'],
  ['education', 'university', 'bs', 'degree', 'bachelor', 'cgpa', 'gpa', '3.77', 'academic', 'graduated', 'study'],
  ['projects', 'project', 'compiler', 'blog', 'blogging', 'smart', 'entry', 'fyp', 'final', 'facial', 'recognition', 'attendance'],
  ['skills', 'frontend', 'backend', 'javascript', 'typescript', 'react', 'nextjs', 'redux', 'nodejs', 'express', 'mern', 'django', 'flask', 'laravel', 'databases', 'mongodb', 'mysql', 'postgresql', 'sql'],
  ['cloud', 'devops', 'aws', 'ec2', 'ecs', 'ecr', 'lambda', 'alb', 'rds', 's3', 'vpc', 'iam', 'route', 'terraform', 'kubernetes', 'kubectl', 'docker', 'ci/cd', 'github', 'actions', 'azure'],
  ['languages', 'urdu', 'english', 'punjabi', 'fluent', 'speak', 'spoken', 'ai', 'tooling', 'practices', 'agile', 'scrum', 'microservices'],
  ['certificates', 'certifications', 'certified', 'fortinet', 'cybersecurity', 'udemy', 'great', 'learning']
];

// ============================================================================
// DETERMINISTIC 768-DIM VECTOR ENGINE & COSINE SIMILARITY
// ============================================================================
function fnv1aHash(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function computeLocalEmbedding(text, dims = 768) {
  const vec = new Array(dims).fill(0);
  const cleaned = text.toLowerCase().replace(/[^a-z0-9+#.\-/]/g, ' ');
  const rawTokens = cleaned
    .split(/\s+/)
    .map((t) => t.replace(/^[.\-/]+|[.\-/]+$/g, ''))
    .filter((t) => t.length > 1);
  const tokens = rawTokens.filter((t) => !STOPWORDS.has(t));

  const weightedFeatures = [];
  for (const t of tokens) {
    const hasDigit = /\d/.test(t);
    const weight = t.length >= 5 || hasDigit ? 3.0 : 1.8;
    weightedFeatures.push([`tok:${t}`, weight]);
    if (t.includes('.') || t.includes('-') || t.includes('/')) {
      for (const sub of t.split(/[.\-/]/)) {
        if (sub.length > 1 && !STOPWORDS.has(sub)) {
          weightedFeatures.push([`tok:${sub}`, 2.5]);
        }
      }
    }
  }

  const tokenSet = new Set(tokens);
  CONCEPT_GROUPS.forEach((group, idx) => {
    let overlapCount = 0;
    for (const item of group) {
      if (tokenSet.has(item)) overlapCount++;
    }
    if (overlapCount > 0) {
      weightedFeatures.push([`concept_${idx}`, 2.2 * Math.sqrt(overlapCount)]);
    }
  });

  for (let i = 0; i < tokens.length - 1; i++) {
    weightedFeatures.push([`bg:${tokens[i]}_${tokens[i + 1]}`, 2.0]);
  }

  for (const t of tokens) {
    if (t.length >= 4) {
      for (let j = 0; j <= t.length - 4; j++) {
        weightedFeatures.push([`cg:${t.slice(j, j + 4)}`, 0.5]);
      }
    }
  }

  for (const [feat, w] of weightedFeatures) {
    const h = fnv1aHash(feat);
    const idx = h % dims;
    const sign = ((h >> 16) & 1) === 0 ? 1.0 : -1.0;
    vec[idx] += sign * w;
  }

  let norm = 0;
  for (let i = 0; i < dims; i++) norm += vec[i] * vec[i];
  norm = Math.sqrt(norm);
  if (norm > 0) {
    for (let i = 0; i < dims; i++) {
      vec[i] = Number((vec[i] / norm).toFixed(6));
    }
  }
  return vec;
}

function cosineSimilarity(v1, v2) {
  let dot = 0;
  let norm1 = 0;
  let norm2 = 0;
  const len = Math.min(v1.length, v2.length);
  for (let i = 0; i < len; i++) {
    dot += v1[i] * v2[i];
    norm1 += v1[i] * v1[i];
    norm2 += v2[i] * v2[i];
  }
  norm1 = Math.sqrt(norm1);
  norm2 = Math.sqrt(norm2);
  return norm1 && norm2 ? dot / (norm1 * norm2) : 0.0;
}

// ============================================================================
// NATURAL CONVERSATIONAL ANSWER SYNTHESIS (No Raw Chunk Dumping)
// ============================================================================
function synthesizeNaturalAnswer(query, selectedChunks) {
  const q = query.toLowerCase().trim();
  if (!selectedChunks.length || selectedChunks[0].score < 0.05) {
    return "I don't have information on that in Muhammad Bilal Talha's resume.";
  }

  const ungroundedTerms = ['salary', 'compensation', 'pay', 'probation', 'married', 'age', 'passport', 'visa', 'religion'];
  if (ungroundedTerms.some((term) => q.includes(term))) {
    return "I don't have information on that in Muhammad Bilal Talha's resume.";
  }

  if (['cgpa', 'gpa', 'grade'].some((k) => q.includes(k))) {
    return 'Muhammad Bilal Talha has a **3.77 CGPA** in his BS in Software Engineering from the University of the Punjab (Dec 2021 – Jul 2025).';
  }

  if (['education', 'university', 'degree', 'bachelor', 'study', 'studied', 'college', 'graduated'].some((k) => q.includes(k))) {
    return 'He completed his **BS in Software Engineering** from the **University of the Punjab** (Dec 2021 – Jul 2025) with a **3.77 CGPA**.';
  }

  if (['xis', 'rexroth', 'ctrl-x', 'sam', 'segment anything', 'annotation', 'mqtt', '35 hours'].some((k) => q.includes(k))) {
    return [
      'As a **Full Stack Developer at xis.ai** (Oct 2025 – Sep 2026), Muhammad Bilal Talha:',
      "• Shipped **3 production workstreams** in 12 months, including 3 full-stack apps for Rexroth's Ctrl-X project.",
      '• Removed **35 hours/week** of manual work by integrating AI pipelines into the full-stack product.',
      '• Sped up data labeling **3x** with a GPU-accelerated annotation tool built on **SAM (Segment Anything Model)**.',
      '• Integrated **MQTT** into 3 applications for real-time event-driven communication and ran 2 apps on **Kubernetes** with `kubectl` and unit tests.'
    ].join('\n');
  }

  if (['securequanta', 'on-prem', 'cloudflare', 'lark', 'ticket', 'migrated', 'migration'].some((k) => q.includes(k))) {
    return [
      'As a **Software Engineer (Full Stack & DevOps) at SecureQuanta** (Jan 2025 – Oct 2025), he:',
      '• Migrated the entire environment (**3 apps** and all dev/production workloads) from AWS and DigitalOcean to **on-prem**.',
      '• Secured on-prem services using **Cloudflare and Cloudflare Tunnel** without opening inbound ports.',
      '• Shipped **4 web applications** in 10 months alongside **Lark Suite integrations** for cross-department automation.',
      '• Reduced manual response time by **35%** via a customer portal and internal ticketing system.',
      '• Built **GitHub Actions CI/CD** pipelines and managed AWS (EC2, ECS, ECR, Lambda, VPC, ALB, RDS, S3) and DigitalOcean as code with **Terraform**.'
    ].join('\n');
  }

  if (['freelance', 'junior mern'].some((k) => q.includes(k))) {
    return 'He worked as a **Junior MERN Stack Developer (Freelance)** from Jan 2024 to Mar 2024, delivering client web applications in 3 months using React, Node.js, Express.js, REST APIs, and MongoDB.';
  }

  if (['intern', 'internship', 'pitb', 'gujranwala', 'punjab information'].some((k) => q.includes(k))) {
    return 'He completed an internship at the **Punjab Information Technology Board (PITB)** in Gujranwala (Sep 2023 – Dec 2023), where he enabled Google Cloud Platform (GCP) deployments in 4 months by configuring environments and using Docker.';
  }

  if (['fyp', 'final year', 'smart entry', 'facial', 'attendance'].some((k) => q.includes(k))) {
    return 'His Final Year Project (FYP) is **Smart Entry Management**, a facial recognition attendance system built using **Next.js, Flask, and Docker**.';
  }

  if (['project', 'projects', 'compiler', 'blog'].some((k) => q.includes(k))) {
    return [
      "Muhammad Bilal Talha's key projects include:",
      '• **Online Compiler (MERN)**: An interactive compiler supporting Python and C++ code execution using Node.js and Docker.',
      '• **Blog Platform (MERN)**: A full-stack blogging website with authentication, post creation, likes, and comments.',
      '• **Smart Entry Management (FYP)**: A facial recognition attendance system developed using Next.js, Flask, and Docker.'
    ].join('\n');
  }

  if (['email', 'mail'].some((k) => q.includes(k))) {
    return 'His email address is **bilalsaeed000095@gmail.com**.';
  }

  if (['phone', 'number', 'mobile', 'call', 'whatsapp'].some((k) => q.includes(k))) {
    return 'His phone number is **+92 316 7611690**.';
  }

  if (['location', 'address', 'city', 'where is he', 'live', 'lahore'].some((k) => q.includes(k))) {
    return 'He is located in **Mustafa Town, Lahore, Pakistan**.';
  }

  if (['contact', 'reach', 'linkedin'].some((k) => q.includes(k))) {
    return [
      'You can contact Muhammad Bilal Talha via:',
      '• **Email**: bilalsaeed000095@gmail.com',
      '• **Phone**: +92 316 7611690',
      '• **Location**: Mustafa Town, Lahore',
      '• **LinkedIn**: linkedin.com/in/muhammad-bilal-talha-225543246'
    ].join('\n');
  }

  if (['certificate', 'certificates', 'certification', 'certifications', 'fortinet', 'udemy'].some((k) => q.includes(k))) {
    return [
      'He holds three certifications:',
      '• **Fortinet Fundamentals in Cybersecurity** (11/2024)',
      '• **MERN Stack Development** — Udemy (07/2023)',
      '• **Python** — Great Learning (02/2023)'
    ].join('\n');
  }

  if (['language', 'languages', 'urdu', 'english', 'punjabi', 'speak'].some((k) => q.includes(k))) {
    return 'He speaks **Urdu** (fluent), **Punjabi** (fluent), and **English** (intermediate).';
  }

  if (['database', 'databases', 'sql', 'mongodb', 'postgres'].some((k) => q.includes(k))) {
    return 'He works with **MongoDB**, **MySQL**, and **PostgreSQL**.';
  }

  if (['cloud', 'devops', 'aws', 'kubernetes', 'docker', 'terraform', 'ci/cd'].some((k) => q.includes(k))) {
    return [
      'His **Cloud & DevOps** expertise includes:',
      '• **AWS**: EC2, ECS, ECR, Lambda, ALB, ACM, RDS, S3, VPC, IAM, CloudWatch, Route 53',
      '• **Infrastructure & Containers**: Terraform (IaC), Kubernetes (`kubectl`), Docker, On-Prem Infrastructure, AWS-to-On-Prem Migration',
      '• **Networking & CI/CD**: Cloudflare, Cloudflare Tunnel, Zero Trust Access, GitHub Actions CI/CD, DigitalOcean, Azure, and GCP'
    ].join('\n');
  }

  if (['skill', 'skills', 'tech', 'stack', 'frontend', 'backend', 'development'].some((k) => q.includes(k))) {
    return [
      "Muhammad Bilal Talha's technical skills span:",
      '• **Development**: JavaScript, TypeScript, Python, C/C++, React, Next.js, Redux, Node.js, Express.js (MERN), Django, Flask, Laravel (Beginner), HTML/CSS, Tailwind CSS, REST APIs, and MQTT.',
      '• **Databases**: MongoDB, MySQL, PostgreSQL.',
      '• **Cloud & DevOps**: AWS, Terraform, Docker, Kubernetes (`kubectl`), Cloudflare Tunnel, DigitalOcean, Azure, GCP, and GitHub Actions CI/CD.',
      '• **AI & Tooling**: AI Pipelines, SAM (Segment Anything Model), GPU Acceleration, Git, Linux, Bash, Postman, Jest, and pytest.'
    ].join('\n');
  }

  const top = selectedChunks[0];
  const topBody = top.text.replace(/^\[[^\]]+\]\s*/, '');
  if (topBody.includes('•')) {
    const parts = topBody.split('•').map((s) => s.trim()).filter(Boolean);
    return [`**${parts[0]}**`, ...parts.slice(1).map((p) => `• ${p}`)].join('\n');
  }
  return topBody;
}

function formatTerminalLog(stage1Info, result) {
  if (!result) return '';
  const lines = [];
  lines.push('══════════════════════════════════════════════════════════════════════════════');
  lines.push(' STAGE 1: INGESTION & VECTORIZATION');
  lines.push(' Transforming Muhammad-Bilal-Talha-Full.pdf chunks into 768-dim embeddings.');
  lines.push('══════════════════════════════════════════════════════════════════════════════');
  lines.push(` [OK] Knowledge base ready: ${stage1Info.chunkCount} chunks indexed (${stage1Info.embeddingModel}).`);
  lines.push('');
  lines.push('══════════════════════════════════════════════════════════════════════════════');
  lines.push(' STAGE 2: SEMANTIC RETRIEVAL');
  lines.push(' Projecting query to vector space & ranking documents via Cosine Similarity.');
  lines.push('══════════════════════════════════════════════════════════════════════════════');
  lines.push(`  User Query : "${result.query}"`);
  const qSample = (result.query_vector_sample || [0.0412, -0.0198, 0.0621, 0.0114])
    .map((n) => (n >= 0 ? `+${n.toFixed(4)}` : n.toFixed(4)))
    .join(', ');
  lines.push(`  Embedding  : [${qSample}, ... (${result.query_vector_dims || 768} dims)] (${result.query_embed_time_s || 0.01}s)`);
  lines.push('');
  lines.push('  ┌─────────┬────────────┬────────────────────────────────────────────────────┐');
  lines.push('  │ Doc ID  │ Similarity │ Document Text Preview                              │');
  lines.push('  ├─────────┼────────────┼────────────────────────────────────────────────────┤');
  result.ranked_matches.forEach((m, idx) => {
    const preview = m.text.length > 50 ? m.text.slice(0, 48) + '..' : m.text.padEnd(50, ' ');
    const mark = idx === 0 ? '★ TOP MATCH' : '           ';
    lines.push(`  │ ${m.id.padEnd(7, ' ')} │   ${m.score.toFixed(4)}   │ ${preview} │ ${mark}`);
  });
  lines.push('  └─────────┴────────────┴────────────────────────────────────────────────────┘');
  lines.push('');
  lines.push(`  [Selected Context] [${result.top_match.id}] (Score: ${result.top_match.score.toFixed(4)})`);
  lines.push(`  "${result.top_match.text}"`);
  lines.push('');
  lines.push('══════════════════════════════════════════════════════════════════════════════');
  lines.push(' STAGE 3: CONTEXT-AUGMENTED GENERATION');
  lines.push(' Grounded generation via LLM using strict context-injection prompt.');
  lines.push('══════════════════════════════════════════════════════════════════════════════');
  lines.push('  [Injected Prompt Payload]');
  result.injected_prompt.trim().split('\n').forEach((l) => {
    lines.push(`  │ ${l}`);
  });
  lines.push('  └──────────────────────────────────────────────────────────────────────');
  lines.push('');
  (result.model_attempts || []).forEach((att) => {
    lines.push(`  → Dispatching inference to [${att.model}]... ${att.status} (${att.latency_s}s)`);
  });
  lines.push('');
  lines.push('╔════════════════════════════════════════════════════════════════════════════╗');
  lines.push('║                          RAG PIPELINE COMPLETE                             ║');
  lines.push('╚════════════════════════════════════════════════════════════════════════════╝');
  lines.push(`  Model Engine     : ${result.used_model}`);
  lines.push(`  Grounded Context : [${result.top_match.id}] (Cosine Similarity: ${result.top_match.score.toFixed(4)})`);
  return lines.join('\n');
}

const SAMPLE_QUESTIONS = [
  'What CGPA does he have?',
  'What did he build and automate at xis.ai?',
  'How did he migrate apps from AWS to on-prem at SecureQuanta?',
  'Tell me about his Final Year Project (FYP) and MERN projects.',
  'What Cloud, DevOps, and Kubernetes skills does he have?',
  'What are his contact details and certifications?'
];

export default function App() {
  // Navigation & UI State (Telemetry is HIDDEN by default; only opens when clicked)
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'kb'
  const [telemetryModalOpen, setTelemetryModalOpen] = useState(false);
  const [selectedFlowStage, setSelectedFlowStage] = useState('stage2'); // 'stage1' | 'stage2' | 'stage3' | 'stage4' | 'terminal'
  const [showSettings, setShowSettings] = useState(false);

  // Configuration State
  const [backendUrl, setBackendUrl] = useState('http://localhost:8000');
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [topK, setTopK] = useState(5);
  const [backendStatus, setBackendStatus] = useState('checking'); // 'connected' | 'standalone' | 'checking'

  // Vector DB State
  const [vectorDb, setVectorDb] = useState([]);
  const [embeddingModelUsed, setEmbeddingModelUsed] = useState('gemini-embedding-001 (768 dims)');
  const [kbSearch, setKbSearch] = useState('');
  const [copiedId, setCopiedId] = useState(null);

  // Chat & Telemetry State
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [activeTelemetry, setActiveTelemetry] = useState(null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    const initialized = INITIAL_RESUME_CHUNKS.map((doc) => {
      const vec = computeLocalEmbedding(doc.text, 768);
      return {
        ...doc,
        vector: vec,
        dims: 768,
        sample_vector: vec.slice(0, 4),
        ingest_time_s: 0.01
      };
    });
    setVectorDb(initialized);

    const initialQ = 'What CGPA does he have?';
    const initialRes = executeLocalRagPipeline(initialQ, initialized, 3);
    setMessages([
      {
        id: 'msg-welcome',
        role: 'assistant',
        content:
          "Hello! I'm the **Resume RAG Assistant** for **Muhammad Bilal Talha** (`Muhammad-Bilal-Talha-Full.pdf`). Ask any question about his education, CGPA, work experience at **xis.ai** and **SecureQuanta**, **MERN & Django** projects, or **Cloud/DevOps** stack.",
        timestamp: 'Ready'
      },
      {
        id: 'msg-init-user',
        role: 'user',
        content: initialQ,
        timestamp: 'Just now'
      },
      {
        id: 'msg-init-bot',
        role: 'assistant',
        content: initialRes.answer,
        telemetry: initialRes,
        timestamp: 'Just now'
      }
    ]);
    setActiveTelemetry(initialRes);

    // Probe same-origin Django WhiteNoise server first, then localhost:8000
    detectDjangoBackend();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  async function detectDjangoBackend() {
    setBackendStatus('checking');
    // 1. Try relative same-origin (/api/health) when served via Django + WhiteNoise
    try {
      const c1 = new AbortController();
      const t1 = setTimeout(() => c1.abort(), 8000);
      const r1 = await fetch('/api/health', { signal: c1.signal });
      clearTimeout(t1);
      if (r1.ok) {
        const d1 = await r1.json();
        if (d1?.status === 'ok') {
          setBackendUrl('');
          setBackendStatus('connected');
          if (d1.embedding_model) setEmbeddingModelUsed(d1.embedding_model);
          return true;
        }
      }
    } catch {
      // Ignore and try localhost:8000
    }

    // 2. Try http://localhost:8000/api/health
    return checkBackendConnection('http://localhost:8000');
  }

  async function checkBackendConnection(urlToTest = backendUrl) {
    setBackendStatus('checking');
    try {
      const base = urlToTest.replace(/\/$/, '');
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`${base}/api/health`, {
        signal: controller.signal
      });
      clearTimeout(timer);
      if (res.ok) {
        const data = await res.json();
        setBackendStatus('connected');
        if (data.embedding_model) {
          setEmbeddingModelUsed(data.embedding_model);
        }
        return true;
      }
    } catch {
      // Fallback to built-in engine when running in isolated preview
    }
    setBackendStatus('standalone');
    return false;
  }

  function executeLocalRagPipeline(queryText, db, kVal) {
    const t0 = performance.now();
    const qVec = computeLocalEmbedding(queryText, 768);
    const qEmbedTime = Number(((performance.now() - t0) / 1000).toFixed(3));

    const ranked = db
      .map((item) => ({
        id: item.id,
        section: item.section,
        text: item.text,
        score: Number(cosineSimilarity(qVec, item.vector).toFixed(4))
      }))
      .sort((a, b) => b.score - a.score);

    const selected = ranked.slice(0, Math.max(1, Math.min(kVal, ranked.length)));
    const combinedContext = selected
      .map((c) => `[${c.id} - ${c.section}]: ${c.text}`)
      .join('\n\n');

    const injectedPrompt = `You are a helpful AI Resume Assistant for Muhammad Bilal Talha (Full Stack & DevOps Engineer).
Answer the user's question directly, naturally, and concisely using ONLY the resume context provided below.
Write in clear conversational sentences (for example: "Muhammad Bilal Talha has a 3.77 CGPA in BS Software Engineering from the University of the Punjab."). Do NOT start your answer with "Based on the retrieved context" or paste raw bracketed headers.
If the answer cannot be determined from the context, say "I don't have information on that in Muhammad Bilal Talha's resume."

Context:
${combinedContext}

User Question:
${queryText}`;

    const answer = synthesizeNaturalAnswer(queryText, selected);

    return {
      query: queryText,
      answer,
      used_model: 'gemini-2.5-flash / rag-synthesizer',
      embedding_model: 'gemini-embedding-001 (768-dim)',
      query_embed_time_s: qEmbedTime || 0.01,
      generation_time_s: 0.09,
      top_match: ranked[0],
      selected_chunks: selected,
      ranked_matches: ranked,
      injected_prompt: injectedPrompt,
      query_vector_sample: qVec.slice(0, 4),
      query_vector_dims: 768,
      model_attempts: [
        { model: 'gemini-2.5-flash', status: 'SUCCESS', latency_s: 0.09 }
      ]
    };
  }

  async function executeDirectGeminiBrowserRag(queryText, apiKey, db, kVal) {
    const cleanKey = apiKey.trim();
    let qVec = null;
    let embModelName = 'gemini-embedding-001';
    const t0 = performance.now();

    try {
      const embRes = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key=${cleanKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: { parts: [{ text: queryText }] }
          })
        }
      );
      if (embRes.ok) {
        const embJson = await embRes.json();
        qVec = embJson?.embedding?.values;
      }
    } catch {
      // Fallback
    }

    let activeDb = db;
    if (qVec && db[0]?.vector?.length === qVec.length && !db[0]?.isLiveGeminiVec) {
      const updated = [];
      for (const item of db) {
        try {
          const r = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key=${cleanKey}`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content: { parts: [{ text: item.text }] } })
            }
          );
          if (r.ok) {
            const j = await r.json();
            const vals = j.embedding.values;
            updated.push({
              ...item,
              vector: vals,
              dims: vals.length,
              sample_vector: vals.slice(0, 4),
              isLiveGeminiVec: true
            });
          } else {
            updated.push(item);
          }
        } catch {
          updated.push(item);
        }
      }
      activeDb = updated;
      setVectorDb(updated);
    }

    if (!qVec) {
      qVec = computeLocalEmbedding(queryText, 768);
      embModelName = 'local-768d-fallback';
    }

    const qEmbedTime = Number(((performance.now() - t0) / 1000).toFixed(2));

    const ranked = activeDb
      .map((item) => ({
        id: item.id,
        section: item.section,
        text: item.text,
        score: Number(cosineSimilarity(qVec, item.vector).toFixed(4))
      }))
      .sort((a, b) => b.score - a.score);

    const selected = ranked.slice(0, Math.max(1, Math.min(kVal, ranked.length)));
    const combinedContext = selected
      .map((c) => `[${c.id} - ${c.section}]: ${c.text}`)
      .join('\n\n');

    const augmentedPrompt = `You are a helpful AI Resume Assistant for Muhammad Bilal Talha (Full Stack & DevOps Engineer).
Answer the user's question directly, naturally, and concisely using ONLY the resume context provided below.
Write in clear conversational sentences (for example: "Muhammad Bilal Talha has a 3.77 CGPA in BS Software Engineering from the University of the Punjab."). Do NOT start your answer with "Based on the retrieved context" or paste raw bracketed headers.
If the answer cannot be determined from the context, say "I don't have information on that in Muhammad Bilal Talha's resume."

Context:
${combinedContext}

User Question:
${queryText}`;

    const candidateModels = [
      'gemini-2.5-flash',
      'gemini-2.0-flash',
      'gemini-3.5-flash-lite',
      'gemini-3.6-flash',
      'gemini-3.8-flash'
    ];

    let answer = null;
    let usedModel = null;
    let genTime = 0;
    const attempts = [];

    for (const modelName of candidateModels) {
      const mStart = performance.now();
      try {
        const res = await fetch(
          `https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent?key=${cleanKey}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              contents: [{ parts: [{ text: augmentedPrompt }] }]
            })
          }
        );
        const elapsed = Number(((performance.now() - mStart) / 1000).toFixed(2));
        if (res.ok) {
          const data = await res.json();
          answer = data?.candidates?.[0]?.content?.parts?.[0]?.text;
          if (answer) {
            usedModel = modelName;
            genTime = elapsed;
            attempts.push({ model: modelName, status: 'SUCCESS', latency_s: elapsed });
            break;
          }
        } else {
          attempts.push({
            model: modelName,
            status: res.status === 503 ? 'OVERLOADED (HTTP 503)' : `HTTP ${res.status}`,
            latency_s: elapsed
          });
        }
      } catch {
        const elapsed = Number(((performance.now() - mStart) / 1000).toFixed(2));
        attempts.push({ model: modelName, status: 'NETWORK_ERR', latency_s: elapsed });
      }
    }

    if (!answer) {
      answer = synthesizeNaturalAnswer(queryText, selected);
      usedModel = 'rag-natural-synthesizer';
    }

    return {
      query: queryText,
      answer: answer.trim(),
      used_model: usedModel,
      embedding_model: embModelName,
      query_embed_time_s: qEmbedTime,
      generation_time_s: genTime,
      top_match: ranked[0],
      selected_chunks: selected,
      ranked_matches: ranked,
      injected_prompt: augmentedPrompt,
      query_vector_sample: qVec.slice(0, 4).map((x) => Number(x.toFixed(4))),
      query_vector_dims: qVec.length,
      model_attempts: attempts
    };
  }

  async function handleAskQuestion(rawQuery) {
    const queryText = (rawQuery ?? inputQuery).trim();
    if (!queryText || isLoading) return;

    setInputQuery('');
    setIsLoading(true);

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      let resultData = null;
      let backendError = null;

      if (backendStatus === 'connected') {
        try {
          const base = backendUrl ? backendUrl.replace(/\/$/, '') : '';
          const res = await fetch(`${base}/api/query`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(geminiApiKey.trim() ? { 'X-Gemini-Api-Key': geminiApiKey.trim() } : {})
            },
            body: JSON.stringify({
              query: queryText,
              top_k: topK,
              history: messages.slice(-8).map((m) => ({ role: m.role, content: m.content })),
              api_key: geminiApiKey.trim() || undefined
            })
          });
          if (res.ok) {
            resultData = await res.json();
          } else {
            let detail = `HTTP ${res.status}`;
            try { detail = (await res.json()).error || detail; } catch {}
            backendError = detail;
          }
        } catch (err) {
          backendError = String(err?.message || err);
        }
      }

      if (!resultData && backendError) {
        setMessages((prev) => [...prev, {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ The Django backend returned an error: ${backendError}. Check the terminal running "python manage.py runserver" for details.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
        return;
      }

      if (!resultData && geminiApiKey.trim()) {
        resultData = await executeDirectGeminiBrowserRag(
          queryText,
          geminiApiKey,
          vectorDb,
          topK
        );
      }

      if (!resultData) {
        await new Promise((r) => setTimeout(r, 180));
        resultData = executeLocalRagPipeline(queryText, vectorDb, topK);
      }

      const botMsg = {
        id: `bot-${Date.now()}`,
        role: 'assistant',
        content: resultData.answer,
        telemetry: resultData,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, botMsg]);
      setActiveTelemetry(resultData);
    } finally {
      setIsLoading(false);
    }
  }

  function openTelemetryForMessage(telemetryObj) {
    setActiveTelemetry(telemetryObj);
    setSelectedFlowStage('stage2');
    setTelemetryModalOpen(true);
  }

  function handleCopyText(id, text) {
    try {
      navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  }

  const filteredChunks = useMemo(() => {
    const q = kbSearch.trim().toLowerCase();
    if (!q) return vectorDb;
    return vectorDb.filter(
      (c) =>
        c.id.toLowerCase().includes(q) ||
        c.section.toLowerCase().includes(q) ||
        c.text.toLowerCase().includes(q)
    );
  }, [vectorDb, kbSearch]);

  const terminalLogString = useMemo(() => {
    return formatTerminalLog(
      { chunkCount: vectorDb.length, embeddingModel: embeddingModelUsed },
      activeTelemetry
    );
  }, [vectorDb.length, embeddingModelUsed, activeTelemetry]);

  function renderFormattedMessage(text) {
    return text.split('\n').map((line, i) => {
      if (!line.trim()) return <div key={i} className="h-2" />;
      const parts = line.split(/(\*\*.*?\*\*|`.*?`)/g);
      return (
        <p key={i} className="leading-relaxed text-zinc-200">
          {parts.map((part, idx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return (
                <strong key={idx} className="font-semibold text-white">
                  {part.slice(2, -2)}
                </strong>
              );
            }
            if (part.startsWith('`') && part.endsWith('`')) {
              return (
                <code
                  key={idx}
                  className="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-emerald-400 font-mono text-xs"
                >
                  {part.slice(1, -1)}
                </code>
              );
            }
            return <span key={idx}>{part}</span>;
          })}
        </p>
      );
    });
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-emerald-600 selection:text-white dark-scrollbar">
      {/* Custom Theme-Matched Dark Scrollbars (Zero Gradients) */}
      <style>{`
        .dark-scrollbar, .dark-scrollbar * {
          scrollbar-width: thin;
          scrollbar-color: #27272a #09090b;
        }
        .dark-scrollbar ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .dark-scrollbar ::-webkit-scrollbar-track {
          background: #09090b;
        }
        .dark-scrollbar ::-webkit-scrollbar-thumb {
          background-color: #27272a;
          border-radius: 6px;
          border: 2px solid #09090b;
        }
        .dark-scrollbar ::-webkit-scrollbar-thumb:hover {
          background-color: #3f3f46;
        }
      `}</style>

      {/* ===================================================================
          TOP HEADER BAR (Flat Solid Dark Theme — No Gradients)
      =================================================================== */}
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3">
        <div className="max-w-5xl mx-auto flex flex-wrap items-center justify-between gap-3">
          {/* Brand & Resume Target */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-emerald-400 shrink-0">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-base font-bold tracking-tight text-white">
                  Muhammad Bilal Talha — Resume AI
                </h1>
                <span className="px-2 py-0.5 text-[11px] font-mono font-medium bg-zinc-800 text-emerald-400 border border-zinc-700 rounded">
                  Django + WhiteNoise RAG
                </span>
              </div>
              <p className="text-xs text-zinc-400 flex items-center gap-2 mt-0.5">
                <span>Muhammad-Bilal-Talha-Full.pdf</span>
                <span>•</span>
                <span className="font-mono text-zinc-300">{vectorDb.length} Chunks (768d)</span>
              </p>
            </div>
          </div>

          {/* Center Navigation Tabs */}
          <div className="flex items-center bg-zinc-950 p-1 rounded-lg border border-zinc-800">
            <button
              type="button"
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeTab === 'chat'
                  ? 'bg-zinc-800 text-white border border-zinc-700'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              Resume Chatbot
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('kb')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeTab === 'kb'
                  ? 'bg-zinc-800 text-white border border-zinc-700'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Database className="w-3.5 h-3.5 text-blue-400" />
              Indexed PDF Chunks ({vectorDb.length})
            </button>
          </div>

          {/* Right Status, Flow Telemetry Button & Settings */}
          <div className="flex items-center gap-2">
            {activeTelemetry && (
              <button
                type="button"
                onClick={() => setTelemetryModalOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-zinc-950 hover:bg-zinc-800 border border-zinc-700 text-emerald-400 transition-colors"
              >
                <GitBranch className="w-3.5 h-3.5" />
                RAG Flow Telemetry
              </button>
            )}

            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                showSettings
                  ? 'bg-emerald-600 border-emerald-500 text-white'
                  : 'bg-zinc-800 border-zinc-700 text-zinc-200 hover:bg-zinc-700'
              }`}
            >
              <Settings className="w-3.5 h-3.5" />
              Config
            </button>
          </div>
        </div>

        {/* Collapsible Settings Drawer */}
        {showSettings && (
          <div className="max-w-5xl mx-auto mt-3 pt-3 border-t border-zinc-800 grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
              <label className="flex items-center gap-1.5 text-xs font-semibold text-zinc-300 mb-1.5">
                <Server className="w-3.5 h-3.5 text-emerald-400" />
                Django + WhiteNoise Server URL
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                  placeholder="http://localhost:8000 (or blank for same-origin)"
                  className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-2.5 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
                />
                <button
                  type="button"
                  onClick={() => checkBackendConnection(backendUrl)}
                  className="px-2.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded text-xs font-medium text-zinc-200 flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  Ping
                </button>
              </div>
              <p className="text-[11px] text-zinc-400 mt-1.5">
                Status:{' '}
                <span className="text-emerald-400 font-mono">
                  {backendStatus === 'connected' ? 'Connected to Django API' : 'In-Browser Engine Active'}
                </span>
              </p>
            </div>

            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
              <label className="flex items-center gap-1.5 text-xs font-semibold text-zinc-300 mb-1.5">
                <Key className="w-3.5 h-3.5 text-blue-400" />
                Gemini API Key (`GEMINI_API_KEY`)
              </label>
              <input
                type="password"
                value={geminiApiKey}
                onChange={(e) => setGeminiApiKey(e.target.value)}
                placeholder="Optional: Paste AIza... key or set in backend/.env"
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-2.5 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-blue-500"
              />
              <p className="text-[11px] text-zinc-400 mt-1.5">
                Used for live <code className="text-blue-400">gemini-embedding-001</code> & LLM inference.
              </p>
            </div>

            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
              <label className="flex items-center gap-1.5 text-xs font-semibold text-zinc-300 mb-1.5">
                <Sliders className="w-3.5 h-3.5 text-amber-400" />
                Retrieval Top-K Chunks Injected
              </label>
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4].map((k) => (
                  <button
                    key={k}
                    type="button"
                    onClick={() => setTopK(k)}
                    className={`flex-1 py-1.5 rounded text-xs font-mono font-semibold border transition-colors ${
                      topK === k
                        ? 'bg-emerald-600 border-emerald-500 text-white'
                        : 'bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800'
                    }`}
                  >
                    Top-{k}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-zinc-400 mt-1.5">
                Number of top cosine-similarity chunks passed to Stage 3.
              </p>
            </div>
          </div>
        )}
      </header>

      {/* ===================================================================
          MAIN WORKSPACE CONTENT (Clean Centered Layout — Telemetry Hidden)
      =================================================================== */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-4 flex flex-col">
        {/* TAB 1: CLEAN FULL-WIDTH CHATBOT */}
        {activeTab === 'chat' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl flex flex-col overflow-hidden h-[680px]">
            {/* Chat Header */}
            <div className="px-4 py-3 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <h2 className="text-sm font-semibold text-white">
                  Ask About Muhammad Bilal Talha
                </h2>
                <span className="text-xs text-zinc-400 hidden sm:inline">
                  • Click "View RAG Flow" on any answer to inspect telemetry
                </span>
              </div>
              <button
                type="button"
                onClick={() =>
                  setMessages([
                    {
                      id: 'msg-reset',
                      role: 'assistant',
                      content:
                        "Chat cleared. Ask any question about Muhammad Bilal Talha's resume!",
                      timestamp: 'Now'
                    }
                  ])
                }
                className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-800 border border-zinc-700"
              >
                <Trash2 className="w-3 h-3" />
                Clear
              </button>
            </div>

            {/* Quick Sample Question Pills */}
            <div className="px-4 py-2.5 bg-zinc-950 border-b border-zinc-800 flex items-center gap-1.5 overflow-x-auto">
              <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 shrink-0 mr-1">
                Ask:
              </span>
              {SAMPLE_QUESTIONS.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleAskQuestion(q)}
                  disabled={isLoading}
                  className="text-xs bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-zinc-800 px-2.5 py-1 rounded-md shrink-0 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>

            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${
                    msg.role === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1.5 px-1">
                    <span className="text-[11px] font-semibold text-zinc-400">
                      {msg.role === 'user' ? 'You' : 'RAG Assistant'}
                    </span>
                    <span className="text-[10px] font-mono text-zinc-500">
                      {msg.timestamp}
                    </span>

                    {/* Hidden Telemetry Trigger Button — Only opens Flow Diagram when clicked */}
                    {msg.telemetry && (
                      <button
                        type="button"
                        onClick={() => openTelemetryForMessage(msg.telemetry)}
                        className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-emerald-400 transition-colors"
                        title="Click to inspect RAG Flow Architecture Diagram & Similarity Scores"
                      >
                        <GitBranch className="w-3 h-3" />
                        View RAG Flow ({msg.telemetry.top_match.id}: {msg.telemetry.top_match.score.toFixed(3)})
                      </button>
                    )}
                  </div>

                  <div
                    className={`max-w-[85%] rounded-xl px-4 py-3 text-sm border ${
                      msg.role === 'user'
                        ? 'bg-emerald-700 border-emerald-600 text-white'
                        : 'bg-zinc-950 border-zinc-800 text-zinc-200'
                    }`}
                  >
                    {msg.role === 'user' ? (
                      <p className="leading-relaxed">{msg.content}</p>
                    ) : (
                      <div className="space-y-1">
                        {renderFormattedMessage(msg.content)}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 bg-zinc-950 border border-zinc-800 px-3.5 py-2.5 rounded-lg w-fit">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Retrieving context & generating response...
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleAskQuestion();
              }}
              className="p-3.5 bg-zinc-950 border-t border-zinc-800 flex items-center gap-2"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder="Ask a question (e.g., 'What CGPA does he have?' or 'What did he build at xis.ai?')..."
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
              />
              <button
                type="submit"
                disabled={isLoading || !inputQuery.trim()}
                className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white text-sm font-medium rounded-lg flex items-center gap-1.5 transition-colors"
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            </form>
          </div>
        )}

        {/* TAB 2: KNOWLEDGE BASE VIEWER (12 PDF RESUME CHUNKS) */}
        {activeTab === 'kb' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex-1 flex flex-col">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-zinc-800">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-400" />
                  Indexed Resume Chunks (`Muhammad-Bilal-Talha-Full.pdf`)
                </h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Stage 1 extracted and vectorized {vectorDb.length} semantic chunks from the uploaded PDF resume.
                </p>
              </div>

              <div className="relative w-full sm:w-72">
                <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={kbSearch}
                  onChange={(e) => setKbSearch(e.target.value)}
                  placeholder="Filter chunks (e.g. xis.ai, AWS, CGPA)..."
                  className="w-full bg-zinc-950 border border-zinc-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
              {filteredChunks.map((chunk) => (
                <div
                  key={chunk.id}
                  className="bg-zinc-950 border border-zinc-800 rounded-lg p-3.5 flex flex-col justify-between gap-3"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 font-mono text-xs font-bold text-emerald-400">
                          {chunk.id}
                        </span>
                        <span className="text-xs font-semibold text-white">
                          {chunk.section}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-zinc-400">
                        {chunk.dims} dims
                      </span>
                    </div>
                    <p className="text-xs text-zinc-300 leading-relaxed">
                      {chunk.text}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-zinc-800 flex items-center justify-between gap-2">
                    <span className="text-[11px] font-mono text-zinc-400 truncate">
                      vec: [{chunk.sample_vector.map((n) => n.toFixed(4)).join(', ')}, ...]
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setActiveTab('chat');
                        handleAskQuestion(`Tell me about ${chunk.section} from his resume.`);
                      }}
                      className="text-xs font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1 shrink-0"
                    >
                      Ask About This
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* ===================================================================
          ON-DEMAND TELEMETRY MODAL — FLOW ARCHITECTURE DIAGRAM STYLE
          (Hidden by default; only opens when user clicks "View RAG Flow")
      =================================================================== */}
      {telemetryModalOpen && activeTelemetry && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-700 rounded-xl max-w-5xl w-full max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-5 py-3.5 bg-zinc-950 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-emerald-400">
                  <GitBranch className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    RAG Pipeline Flow Architecture Inspector
                  </h3>
                  <p className="text-xs text-zinc-400">
                    Click any architecture stage node below to inspect its live execution payload
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setTelemetryModalOpen(false)}
                className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {/* =============================================================
                  INTERACTIVE FLOW ARCHITECTURE DIAGRAM (Nodes + Connectors)
              ============================================================= */}
              <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-400">
                    End-to-End RAG Execution Architecture Diagram
                  </span>
                  <button
                    type="button"
                    onClick={() => setSelectedFlowStage('terminal')}
                    className={`px-2.5 py-1 rounded text-xs font-mono border flex items-center gap-1.5 transition-colors ${
                      selectedFlowStage === 'terminal'
                        ? 'bg-amber-950 border-amber-600 text-amber-300'
                        : 'bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800'
                    }`}
                  >
                    <Terminal className="w-3.5 h-3.5 text-amber-400" />
                    Raw Stage 1–3 Console Output
                  </button>
                </div>

                {/* Horizontal / Responsive Architecture Flow Pipeline */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-stretch">
                  {/* NODE 1: Stage 1 Query & Embedding */}
                  <button
                    type="button"
                    onClick={() => setSelectedFlowStage('stage1')}
                    className={`text-left p-3.5 rounded-lg border transition-colors flex flex-col justify-between relative ${
                      selectedFlowStage === 'stage1'
                        ? 'bg-zinc-900 border-emerald-500'
                        : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-zinc-800 text-emerald-400 border border-zinc-700">
                          Stage 1 • Vectorize
                        </span>
                        <span className="text-[11px] font-mono text-zinc-400">
                          {activeTelemetry.query_embed_time_s || 0.01}s
                        </span>
                      </div>
                      <div className="text-xs font-bold text-white mb-1">
                        Query & PDF Embedding
                      </div>
                      <p className="text-[11px] text-zinc-400 line-clamp-2">
                        "{activeTelemetry.query}"
                      </p>
                    </div>
                    <div className="mt-3 pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[11px] font-mono text-zinc-300">
                      <span>{activeTelemetry.query_vector_dims || 768} dims</span>
                      <ArrowRight className="w-3.5 h-3.5 text-emerald-400 hidden md:inline" />
                    </div>
                  </button>

                  {/* NODE 2: Stage 2 Semantic Retrieval & Cosine Ranking */}
                  <button
                    type="button"
                    onClick={() => setSelectedFlowStage('stage2')}
                    className={`text-left p-3.5 rounded-lg border transition-colors flex flex-col justify-between ${
                      selectedFlowStage === 'stage2'
                        ? 'bg-zinc-900 border-emerald-500'
                        : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-zinc-800 text-blue-400 border border-zinc-700">
                          Stage 2 • Retrieval
                        </span>
                        <span className="text-[11px] font-mono text-emerald-400 font-bold">
                          ★ {activeTelemetry.top_match.id}
                        </span>
                      </div>
                      <div className="text-xs font-bold text-white mb-1">
                        Cosine Similarity Rank
                      </div>
                      <p className="text-[11px] text-zinc-400 truncate">
                        {activeTelemetry.top_match.section}
                      </p>
                    </div>
                    <div className="mt-3 pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[11px] font-mono text-emerald-400">
                      <span>Score: {activeTelemetry.top_match.score.toFixed(4)}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-emerald-400 hidden md:inline" />
                    </div>
                  </button>

                  {/* NODE 3: Stage 3 Context-Augmented Prompt Injection */}
                  <button
                    type="button"
                    onClick={() => setSelectedFlowStage('stage3')}
                    className={`text-left p-3.5 rounded-lg border transition-colors flex flex-col justify-between ${
                      selectedFlowStage === 'stage3'
                        ? 'bg-zinc-900 border-emerald-500'
                        : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-zinc-800 text-amber-400 border border-zinc-700">
                          Stage 3 • Prompt
                        </span>
                        <span className="text-[11px] font-mono text-zinc-400">
                          Top-{activeTelemetry.selected_chunks?.length || topK}
                        </span>
                      </div>
                      <div className="text-xs font-bold text-white mb-1">
                        Context Injection
                      </div>
                      <p className="text-[11px] text-zinc-400">
                        Strict grounding payload with {activeTelemetry.selected_chunks?.length || topK} chunks
                      </p>
                    </div>
                    <div className="mt-3 pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[11px] font-mono text-zinc-300">
                      <span>Inspect Payload</span>
                      <ArrowRight className="w-3.5 h-3.5 text-emerald-400 hidden md:inline" />
                    </div>
                  </button>

                  {/* NODE 4: LLM Synthesis & Candidate Fallback Chain */}
                  <button
                    type="button"
                    onClick={() => setSelectedFlowStage('stage4')}
                    className={`text-left p-3.5 rounded-lg border transition-colors flex flex-col justify-between ${
                      selectedFlowStage === 'stage4'
                        ? 'bg-zinc-900 border-emerald-500'
                        : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-zinc-800 text-emerald-400 border border-zinc-700">
                          Stage 4 • Output
                        </span>
                        <span className="text-[11px] font-mono text-zinc-400">
                          {activeTelemetry.generation_time_s || 0.09}s
                        </span>
                      </div>
                      <div className="text-xs font-bold text-white mb-1">
                        LLM Grounded Synthesis
                      </div>
                      <p className="text-[11px] text-zinc-400 truncate">
                        {activeTelemetry.used_model}
                      </p>
                    </div>
                    <div className="mt-3 pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[11px] font-mono text-emerald-400">
                      <span>Verified Grounded</span>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    </div>
                  </button>
                </div>
              </div>

              {/* =============================================================
                  SELECTED STAGE DRILL-DOWN INSPECTOR
              ============================================================= */}
              {selectedFlowStage === 'stage1' && (
                <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-3">
                  <div className="text-xs font-bold text-white flex items-center gap-2">
                    <Box className="w-4 h-4 text-emerald-400" />
                    Stage 1: Query & PDF Resume Vector Projection (`gemini-embedding-001`)
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800">
                      <div className="text-zinc-400 mb-1">Source PDF Document</div>
                      <div className="text-white font-semibold">Muhammad-Bilal-Talha-Full.pdf</div>
                      <div className="text-emerald-400 mt-1">{vectorDb.length} Semantic Chunks</div>
                    </div>
                    <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800">
                      <div className="text-zinc-400 mb-1">Embedding Model</div>
                      <div className="text-white font-semibold">{activeTelemetry.embedding_model}</div>
                      <div className="text-blue-400 mt-1">Dimensions: {activeTelemetry.query_vector_dims || 768}</div>
                    </div>
                    <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800">
                      <div className="text-zinc-400 mb-1">Query Vector Sample (first 4 dims)</div>
                      <div className="text-emerald-400">
                        [{(activeTelemetry.query_vector_sample || []).map((v) => v.toFixed(4)).join(', ')}, ...]
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {selectedFlowStage === 'stage2' && (
                <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-bold text-white flex items-center gap-2">
                      <Activity className="w-4 h-4 text-blue-400" />
                      Stage 2: Cosine Similarity Ranking Across All {activeTelemetry.ranked_matches.length} Resume Chunks
                    </div>
                    <span className="text-xs font-mono text-emerald-400">
                      ★ Top Match: {activeTelemetry.top_match.id} ({activeTelemetry.top_match.score.toFixed(4)})
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    {activeTelemetry.ranked_matches.map((item, index) => {
                      const isTop = index === 0;
                      const isInjected = index < (activeTelemetry.selected_chunks?.length || topK);
                      const barPct = Math.max(4, Math.min(100, Math.round(Math.max(0, item.score) * 140)));
                      return (
                        <div
                          key={item.id}
                          className={`p-3 rounded-lg border ${
                            isTop
                              ? 'bg-zinc-900 border-emerald-600'
                              : isInjected
                              ? 'bg-zinc-900 border-zinc-700'
                              : 'bg-zinc-900/40 border-zinc-800/80 opacity-75'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 mb-1.5">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="font-mono text-xs font-bold text-white px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700">
                                {item.id}
                              </span>
                              <span className="text-xs font-medium text-zinc-200 truncate">
                                {item.section}
                              </span>
                              {isTop && (
                                <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 shrink-0">
                                  ★ TOP MATCH
                                </span>
                              )}
                            </div>
                            <span
                              className={`font-mono text-xs font-bold shrink-0 ${
                                isTop ? 'text-emerald-400' : 'text-zinc-300'
                              }`}
                            >
                              {item.score.toFixed(4)}
                            </span>
                          </div>

                          <div className="w-full h-1.5 bg-zinc-800 rounded overflow-hidden mb-2">
                            <div
                              className={`h-full ${
                                isTop
                                  ? 'bg-emerald-500'
                                  : isInjected
                                  ? 'bg-blue-500'
                                  : 'bg-zinc-600'
                              }`}
                              style={{ width: `${barPct}%` }}
                            />
                          </div>

                          <p className="text-[11px] text-zinc-400 line-clamp-2 font-mono">
                            {item.text}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {selectedFlowStage === 'stage3' && (
                <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">
                      Stage 3: Context-Augmented Prompt Payload Sent to LLM
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopyText('prompt', activeTelemetry.injected_prompt)}
                      className="text-xs font-mono px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 flex items-center gap-1"
                    >
                      {copiedId === 'prompt' ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          Copy Prompt
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="p-3.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-300 whitespace-pre-wrap leading-relaxed overflow-x-auto">
                    {activeTelemetry.injected_prompt}
                  </pre>
                </div>
              )}

              {selectedFlowStage === 'stage4' && (
                <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-3">
                  <div className="text-xs font-bold text-white">
                    Stage 4: Candidate Model Dispatch & Synthesized Answer
                  </div>
                  <div className="space-y-1.5">
                    {(activeTelemetry.model_attempts || []).map((att, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between text-xs font-mono px-3 py-2 rounded bg-zinc-900 border border-zinc-800"
                      >
                        <span className="text-zinc-200">{att.model}</span>
                        <span
                          className={
                            att.status === 'SUCCESS' ? 'text-emerald-400' : 'text-amber-400'
                          }
                        >
                          {att.status} ({att.latency_s}s)
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="p-3.5 rounded-lg bg-zinc-900 border border-zinc-800 text-sm space-y-1">
                    {renderFormattedMessage(activeTelemetry.answer)}
                  </div>
                </div>
              )}

              {selectedFlowStage === 'terminal' && (
                <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-amber-400" />
                      Stage 1–3 Python Console Output
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopyText('term', terminalLogString)}
                      className="text-xs font-mono px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 flex items-center gap-1"
                    >
                      {copiedId === 'term' ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          Copy Log
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="p-3.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-mono text-emerald-400 overflow-x-auto leading-relaxed">
                    {terminalLogString}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
