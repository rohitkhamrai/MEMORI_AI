# MemoriaAI Demo Flow

This guide ensures a deterministic, highly impressive product demo that tells the narrative: **"Normal systems forget. MemoriaAI remembers."**

If anything breaks, follow these exact steps to reset and re-record in minutes.

---

## 1. Startup Steps & Environment

Ensure you are in the project root with the correct Python environment activated (e.g. `venv\Scripts\activate` on Windows).

**A. Start the Database**
```bash
docker run --name memoria-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password -d neo4j:latest
```

**B. Start the Backend API**
```bash
cd memoria
uvicorn memoria.api.main:app --reload --port 8000
```

**C. Start the Frontend App**
*(In a new terminal)*
```bash
cd frontend
npm run dev
```

---

## 2. Seed the Dataset (Crucial Step)

Before recording, you MUST seed the database to bypass the "empty graph" stage.

```bash
# From the project root with the venv active
python scripts/seed_demo_dataset.py
```
*Expected Output: "✅ Demo Dataset seeded successfully! Entities: ~550, Relationships: ~2200"*

---

## 3. The Video Recording Flow

Do NOT freestyle. Follow this sequence exactly.

### Step 1: Open Knowledge Evolution Dashboard
1. Navigate to the `Knowledge Evolution` tab.
2. **Show the Metrics:** Hover or point to **Memory Reuse Rate**, **Searches Avoided**, and **Learning Efficiency**. 
3. **Narrative:** "Instead of treating research as disposable, this system accumulates knowledge. You can see our current reuse rate and hours of API search time avoided."

### Step 2: Open Memory Explorer
1. Navigate to the `Memory Explorer` tab.
2. **Show the Graph Stats:** Point out the 500+ entities and 2000+ relationships.
3. **Narrative:** "This isn't just a vector database of documents. It's an evolving graph of claims, entities, and relationships, continually verified against each other."

### Step 3: Run the Research Query
1. Navigate to the `Research` tab.
2. Use this EXACT deterministic query:
   > *"Compare LangGraph, CrewAI, AutoGen and OpenAI Swarm for enterprise multi-agent systems"*
3. Click Submit.
4. **Narrative:** "Let's ask a complex question. The system queries its memory *first*. It identifies what it already knows, detects exact knowledge gaps, and only runs targeted searches to fill those specific gaps."

### Step 4: Show Memory Coverage & The Report
1. Wait for the report to generate (usually 5-15 seconds).
2. Look at the **Research Metadata** sidebar on the right.
3. **CRITICAL: Point to Memory Coverage.**
   - "Notice the Memory Coverage percentage. A large portion of this answer was constructed instantly and for free from memory."
4. Scroll through the generated report tabs (`Summary`, `Claims`, `Contradictions`).
   - "It didn't just summarize text; it extracted new claims, identified contradictions across sources, and added them to the graph."

### Step 5: Close the Learning Loop
1. Navigate back to the `Knowledge Evolution` tab.
2. **Show the updated metrics:** Point out that the graph size increased and the reuse rate or efficiency metrics adjusted.
3. **Narrative:** "Every time we ask a question, the system gets smarter, faster, and cheaper for the next query."

---

## Troubleshooting

If the demo behaves unpredictably or you make a mistake:
1. Re-run `python scripts/seed_demo_dataset.py` to wipe the graph and re-seed to a known good state.
2. Restart the recording from Step 1.
