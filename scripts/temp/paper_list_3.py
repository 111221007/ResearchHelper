# Let's create a comprehensive table of 200 papers related to serverless computing benchmarking
# including all the papers we found and extending with additional high-quality papers

papers = [
    # 2024-2025 Recent Papers
    {
        "id": 1,
        "title": "RL-Based Approach to Enhance Reliability and Efficiency in Autoscaling for Heterogeneous Edge Serverless Computing Environments",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "Reliability, Performance, Resource Management",
        "pdf_link": "https://ieeexplore.ieee.org/document/10858932/",
        "doi": "10.1109/...",
        "keywords": "reliability, efficiency, autoscaling, edge computing, latency, resource management"
    },
    {
        "id": 2,
        "title": "Optimizing Cold Start Performance in Serverless Computing Environments",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "Latency, Performance",
        "pdf_link": "https://ieeexplore.ieee.org/document/10896391/",
        "doi": "10.1109/...",
        "keywords": "cold start, latency, performance, reliability"
    },
    {
        "id": 3,
        "title": "A Low-Latency Edge-Cloud Serverless Computing Framework with a Multi-Armed Bandit Scheduler",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "Latency, Resource Management",
        "pdf_link": "https://ieeexplore.ieee.org/document/10592558/",
        "doi": "10.1109/...",
        "keywords": "low-latency, edge-cloud, scheduling, multi-armed bandit"
    },
    {
        "id": 4,
        "title": "FUYAO: DPU-enabled Direct Data Transfer for Serverless Computing",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "ACM",
        "category": "Latency, Performance",
        "pdf_link": "https://dl.acm.org/doi/10.1145/3620666.3651327",
        "doi": "10.1145/3620666.3651327",
        "keywords": "data transfer, latency, DPU, performance"
    },
    {
        "id": 5,
        "title": "Tackling Cold Start in Serverless Computing with Multi-Level Container Reuse",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "Latency, Resource Management",
        "pdf_link": "https://ieeexplore.ieee.org/document/10579145/",
        "doi": "10.1109/...",
        "keywords": "cold start, container reuse, resource management"
    },
    {
        "id": 6,
        "title": "FIAless: Asynchronous Programming for Large-Scale Burst Requests in Serverless Computing",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "Performance, Resource Management",
        "pdf_link": "https://ieeexplore.ieee.org/document/11083138/",
        "doi": "10.1109/...",
        "keywords": "asynchronous programming, burst requests, performance"
    },
    {
        "id": 7,
        "title": "KneeScale: Efficient Resource Scaling for Serverless Computing at the Edge",
        "authors": "Anonymous",
        "year": 2022,
        "venue": "IEEE",
        "category": "Resource Management, Performance",
        "pdf_link": "https://ieeexplore.ieee.org/document/9826051/",
        "doi": "10.1109/...",
        "keywords": "resource scaling, edge computing, auto-scaling"
    },
    {
        "id": 8,
        "title": "Towards Quality of Experience Fairness for Serverless Functions",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "QoS, Resource Management",
        "pdf_link": "https://ieeexplore.ieee.org/document/10631094/",
        "doi": "10.1109/...",
        "keywords": "QoS, fairness, resource allocation"
    },
    {
        "id": 9,
        "title": "Enabling HPC Scientific Workflows for Serverless",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "Resource Management, Performance",
        "pdf_link": "https://ieeexplore.ieee.org/document/10820688/",
        "doi": "10.1109/...",
        "keywords": "HPC, scientific workflows, resource management"
    },
    {
        "id": 10,
        "title": "Optimizing Resource Management in Serverless Computing: A Dynamic Adaptive Scaling Approach",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "Resource Management, Cost",
        "pdf_link": "https://ieeexplore.ieee.org/document/10724128/",
        "doi": "10.1109/...",
        "keywords": "dynamic scaling, resource management, cost optimization"
    },
    {
        "id": 11,
        "title": "ATOM: AI-Powered Sustainable Resource Management for Serverless Edge Computing Environments",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "Resource Management, Energy Consumption",
        "pdf_link": "https://ieeexplore.ieee.org/document/10376318/",
        "doi": "10.1109/...",
        "keywords": "AI, sustainable computing, edge computing, energy efficiency"
    },
    {
        "id": 12,
        "title": "Resource Management in Serverless Computing - Review, Research Challenges, and Prospects",
        "authors": "Anonymous",
        "year": 2023,
        "venue": "IEEE",
        "category": "Resource Management, Survey",
        "pdf_link": "https://ieeexplore.ieee.org/document/10249574/",
        "doi": "10.1109/...",
        "keywords": "resource management, survey, QoS"
    },
    {
        "id": 13,
        "title": "Joint Resource Management and Pricing for Task Offloading in Serverless Edge Computing",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "IEEE",
        "category": "Resource Management, Cost",
        "pdf_link": "https://ieeexplore.ieee.org/document/10329995/",
        "doi": "10.1109/...",
        "keywords": "resource allocation, pricing, edge computing, energy efficiency"
    },
    {
        "id": 14,
        "title": "Toward security quantification of serverless computing",
        "authors": "Anonymous",
        "year": 2024,
        "venue": "Springer",
        "category": "Security, Privacy",
        "pdf_link": "https://journalofcloudcomputing.springeropen.com/articles/10.1186/s13677-024-00703-y",
        "doi": "10.1186/s13677-024-00703-y",
        "keywords": "security quantification, attack tree, privacy"
    },
    {
        "id": 15,
        "title": "On the Power Consumption of Serverless Functions: An Evaluation of OpenFaaS",
        "authors": "Abdulaziz Alhindi, Karim Djemame, Fatemeh Banaie Heravan",
        "year": 2022,
        "venue": "IEEE Conference",
        "category": "Energy Consumption",
        "pdf_link": "https://eprints.whiterose.ac.uk/id/eprint/193714/1/cifs2022-final.pdf",
        "doi": "10.1109/...",
        "keywords": "power consumption, energy efficiency, OpenFaaS"
    },
    {
        "id": 16,
        "title": "A Performance Benchmark for Serverless Function Triggers",
        "authors": "Joel Scheuner",
        "year": 2022,
        "venue": "IEEE IC2E",
        "category": "Performance, Benchmarking",
        "pdf_link": "https://joelscheuner.com/publication/scheuner-22-ic2e/scheuner-22-ic2e.pdf",
        "doi": "10.1109/...",
        "keywords": "performance benchmark, function triggers, distributed tracing"
    },
    {
        "id": 17,
        "title": "Designing Quality of Service aware Serverless Platforms",
        "authors": "Sheshadri Kalkunte Ramachandra",
        "year": 2024,
        "venue": "IISc Thesis",
        "category": "QoS",
        "pdf_link": "https://etd.iisc.ac.in/handle/2005/6728",
        "doi": "N/A",
        "keywords": "QoS, serverless platforms, resource allocation"
    },
    {
        "id": 18,
        "title": "ENERGY-EFFICIENT AND COST-EFFECTIVE SERVERLESS COMPUTING",
        "authors": "Neetu Gangwani",
        "year": 2024,
        "venue": "IJRCAIT",
        "category": "Energy Consumption, Cost",
        "pdf_link": "https://iaeme.com/MasterAdmin/Journal_uploads/IJRCAIT/VOLUME_7_ISSUE_2/IJRCAIT_07_02_049.pdf",
        "doi": "N/A",
        "keywords": "energy efficiency, cost effectiveness, green computing"
    },
    {
        "id": 19,
        "title": "Practical Cloud Workloads for Serverless FaaS",
        "authors": "Anonymous",
        "year": 2019,
        "venue": "ACM",
        "category": "Benchmarking",
        "pdf_link": "https://dl.acm.org/doi/10.1145/3357223.3365439",
        "doi": "10.1145/3357223.3365439",
        "keywords": "workloads, FaaS, benchmarking, evaluation"
    },
    {
        "id": 20,
        "title": "FunctionBench: A Suite of Workloads for Serverless Cloud Function Service",
        "authors": "Anonymous",
        "year": 2019,
        "venue": "IEEE",
        "category": "Benchmarking",
        "pdf_link": "https://ieeexplore.ieee.org/document/8814583/",
        "doi": "10.1109/...",
        "keywords": "benchmark, workloads, cloud functions"
    }
]

# Let's add more papers to reach closer to 200
additional_papers = [
    {
        "id": 21,
        "title": "Analyzing Tail Latency in Serverless Clouds with STeLLAR",
        "authors": "Anonymous",
        "year": 2021,
        "venue": "IEEE",
        "category": "Latency, Benchmarking",
        "pdf_link": "https://ieeexplore.ieee.org/document/9668286/",
        "doi": "10.1109/...",
        "keywords": "tail latency, performance characterization, benchmarking"
    },
    {
        "id": 22,
        "title": "Benchmarking Serverless Computing Platforms",
        "authors": "Martins Horácio, Araujo Filipe, da Cunha Paulo Rupino",
        "year": 2020,
        "venue": "Springer",
        "category": "Benchmarking",
        "pdf_link": "https://link.springer.com/article/10.1007/s10723-020-09523-1",
        "doi": "10.1007/s10723-020-09523-1",
        "keywords": "benchmarking, performance evaluation, cloud platforms"
    },
    {
        "id": 23,
        "title": "SeBS: A Serverless Benchmark Suite for Function-as-a-Service Computing",
        "authors": "Marcin Copik, Grzegorz Kwasniewski, Maciej Besta, Michal Podstawski, Torsten Hoefler",
        "year": 2021,
        "venue": "ACM Middleware",
        "category": "Benchmarking",
        "pdf_link": "https://arxiv.org/pdf/2012.14132.pdf",
        "doi": "10.1145/3464298.3476133",
        "keywords": "benchmark suite, FaaS, performance evaluation"
    },
    {
        "id": 24,
        "title": "Performance Evaluation Of Amazon's, Google's, And Microsoft's Serverless Functions",
        "authors": "Fahim Uz Zaman, Abdul Hafeez Khan, Muhammad Owais",
        "year": 2021,
        "venue": "IJSTR",
        "category": "Performance, Benchmarking",
        "pdf_link": "https://www.ijstr.org/final-print/apr2021/Performance-Evaluation-Of-Amazons-Googles-And-Microsofts-Serverless-Functions-A-Comparative-Study.pdf",
        "doi": "N/A",
        "keywords": "AWS Lambda, Google Cloud Functions, Azure Functions"
    },
    {
        "id": 25,
        "title": "Function-as-a-Service Benchmarking Framework",
        "authors": "Roland Pellegrini, Igor Ivkic, Markus Tauber",
        "year": 2019,
        "venue": "SCITEPRESS",
        "category": "Benchmarking",
        "pdf_link": "https://www.scitepress.org/Papers/2019/77573/77573.pdf",
        "doi": "10.5220/0007757301990210",
        "keywords": "benchmarking framework, FaaS, performance evaluation"
    },
    {
        "id": 26,
        "title": "Rise of the Planet of Serverless Computing: A Systematic Review",
        "authors": "Multiple Authors",
        "year": 2022,
        "venue": "arXiv",
        "category": "Survey",
        "pdf_link": "https://arxiv.org/pdf/2206.12275.pdf",
        "doi": "arXiv:2206.12275",
        "keywords": "systematic review, serverless computing, performance optimization"
    },
    {
        "id": 27,
        "title": "An Application-Centric Benchmarking Framework for FaaS Platforms",
        "authors": "Martin Grambow, Tobias Pfandzelter, et al.",
        "year": 2021,
        "venue": "arXiv",
        "category": "Benchmarking",
        "pdf_link": "https://arxiv.org/pdf/2102.12770.pdf",
        "doi": "arXiv:2102.12770",
        "keywords": "application-centric, benchmarking, FaaS platforms"
    },
    {
        "id": 28,
        "title": "Function-as-a-Service Performance Evaluation: A Multivocal Literature Review",
        "authors": "Joel Scheuner, Philipp Leitner",
        "year": 2020,
        "venue": "arXiv",
        "category": "Survey, Performance",
        "pdf_link": "https://arxiv.org/pdf/2004.03276.pdf",
        "doi": "arXiv:2004.03276",
        "keywords": "performance evaluation, literature review, FaaS"
    },
    {
        "id": 29,
        "title": "Towards Seamless Serverless Computing Across an Edge-Cloud Continuum",
        "authors": "Emilian Simion, Yuandou Wang, et al.",
        "year": 2024,
        "venue": "arXiv",
        "category": "Edge Computing",
        "pdf_link": "https://arxiv.org/pdf/2401.02271.pdf",
        "doi": "arXiv:2401.02271",
        "keywords": "edge-cloud, orchestration, serverless deployment"
    },
    {
        "id": 30,
        "title": "Understanding Performance Variability of Cloud Serverless Platforms",
        "authors": "Trever Schirmer, et al.",
        "year": 2023,
        "venue": "arXiv",
        "category": "Performance",
        "pdf_link": "https://arxiv.org/pdf/2304.07177.pdf",
        "doi": "arXiv:2304.07177",
        "keywords": "performance variability, cloud platforms"
    }
]

# Combine all papers
all_papers = papers + additional_papers

print(f"Currently collected: {len(all_papers)} papers")
print("\nSample of papers collected:")
for i, paper in enumerate(all_papers[:]):
    print(f"{i+1}. {paper['title']}")
    print(f"   Authors: {paper['authors']}")
    print(f"   Year: {paper['year']}")
    print(f"   Venue: {paper['venue']}")
    print(f"   PDF: {paper['pdf_link']}")
    print(f"   Category: {paper['category']}")
    print()