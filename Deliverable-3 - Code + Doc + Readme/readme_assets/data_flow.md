---
config:
  layout: elk
  theme: neo-dark
---
flowchart LR
 subgraph Client["🌐 Client Interface"]
    direction TB
        WEB(["React Web / PWA"])
        MOBILE(["React Native"])
        STREAM(["Streamlit Dev"])
  end
 subgraph API["🔌 API Gateway"]
        FAST["FastAPI Server<br>Port 8000"]
        SOCK["WebSocket Mgr"]
  end
 subgraph Core["🧠 Orchestrator & Planner"]
    direction TB
        PLANNER{{"Plan Executor<br>Step Tracking"}}
        ROUTER{"Intent Router"}
        LLM_NODE["Llama 3.2 / Gemma<br>Thinking &amp; Analysis"]
  end
 subgraph State_Img["🖼️ Image Context"]
        CUR_IMG[("Current Image")]
        ORG_IMG[("Original Image")]
        HIST_IMG[("Image History<br>(Undo Stack)")]
  end
 subgraph State_Data["📊 Execution Context"]
        SESSION[("Session Metadata<br>ID | Timestamp")]
        PLAN_DATA[("Plan & Steps")]
        CHAT_HIST[("Conversation<br>History")]
  end
 subgraph State_Inter["🧩 Intermediate Artifacts"]
        INT_RES[("Intermediate<br>Results &amp; Images")]
        CACHE_DET[("Cached<br>Detections")]
        CACHE_SEG[("Cached<br>Segmentations")]
  end
 subgraph State["💾 Active GraphState"]
    direction TB
        State_Img
        State_Data
        State_Inter
  end
 subgraph Models["🤖 Model Pipeline"]
    direction TB
        m_DET["YOLO11n<br>Detection"]
        m_SEG["MobileSAM<br>Segmentation"]
        m_DEPTH["Depth-Anything<br>Depth Map"]
        m_GEN["MI-GAN / SwinIR<br>Inpaint &amp; SR"]
  end
    WEB -- HTTPS / WSS --> FAST
    MOBILE -- HTTPS / WSS --> FAST
    STREAM -- Direct --> PLANNER & ROUTER
    FAST <-- Stream --> SOCK
    FAST -- Request --> ROUTER
    SOCK -. Push Updates .-> WEB
    ROUTER -- Analyze --> LLM_NODE
    LLM_NODE -- Gen Plan --> PLANNER
    PLANNER <-- RW: Step & Status --> PLAN_DATA
    PLANNER -- Update --> CHAT_HIST
    PLANNER -- Set --> CUR_IMG
    PLANNER -- "1. Dispatch Tool" --> Models
    Models -- "2. Input" --> CUR_IMG
    m_DET -- "3. Write Result" --> CACHE_DET
    m_DET -- Overlay --> INT_RES
    m_SEG -- "3. Write Mask" --> CACHE_SEG
    m_GEN -- "3. New Image" --> CUR_IMG
    m_GEN -- Save Previous --> HIST_IMG
    m_GEN -- Snapshot --> INT_RES
    CUR_IMG -. Final Render .-> FAST

     WEB:::client
     MOBILE:::client
     STREAM:::client
     FAST:::api
     SOCK:::api
     PLANNER:::core
     ROUTER:::core
     LLM_NODE:::core
     CUR_IMG:::state
     ORG_IMG:::state
     HIST_IMG:::state
     SESSION:::state
     PLAN_DATA:::state
     CHAT_HIST:::state
     INT_RES:::state
     CACHE_DET:::state
     CACHE_SEG:::state
     m_DET:::model
     m_SEG:::model
     m_DEPTH:::model
     m_GEN:::model
    classDef client fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1
    classDef api fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#bf360c
    classDef core fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c
    classDef state fill:#ffebee,stroke:#c62828,stroke-width:2px,stroke-dasharray: 5 5,color:#b71c1c
    classDef model fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20
    classDef storage fill:#eceff1,stroke:#546e7a,stroke-width:2px,color:#263238