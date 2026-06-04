import os
import sys
import random
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from memoria.database.neo4j_client import Neo4jClient

def seed_demo_dataset():
    print("🌱 Connecting to Neo4j to seed MemoriaAI Demo Dataset...")
    client = Neo4jClient(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "password")
    )
    
    if not client.verify_connection():
        print("❌ Could not connect to Neo4j. Please ensure Docker container is running.")
        return
        
    print("🧹 Wiping existing database...")
    with client.driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        
    print("🧬 Generating 500+ Entities and 2000+ Relationships...")
    
    domains = ["Quantum Physics", "Artificial Intelligence", "Renewable Energy", "Space Exploration", "Biotechnology"]
    
    entities = []
    
    # Generate Entities
    for i in range(550):
        domain = random.choice(domains)
        entities.append({
            "name": f"Concept_{domain[:3]}_{i}",
            "type": "Concept",
            "description": f"A foundational concept in {domain}.",
            "community_id": domains.index(domain)
        })
        
    # Inject Entities
    with client.driver.session() as session:
        for chunk in [entities[i:i + 100] for i in range(0, len(entities), 100)]:
            session.run("""
                UNWIND $nodes AS node
                MERGE (n:Entity {id: node.name})
                SET n.name = node.name, 
                    n.type = node.type,
                    n.description = node.description,
                    n.community_id = node.community_id,
                    n.created_at = datetime()
            """, nodes=chunk)

    # Generate Relationships
    relationships = []
    predicates = ["DEPENDS_ON", "RELATES_TO", "ENABLES", "CONTRADICTS", "EVOLVED_FROM"]
    
    for i in range(2200):
        source = random.choice(entities)["name"]
        target = random.choice(entities)["name"]
        while target == source:
            target = random.choice(entities)["name"]
            
        relationships.append({
            "source": source,
            "target": target,
            "predicate": random.choice(predicates),
            "confidence": round(random.uniform(0.7, 1.0), 2),
            "source_url": f"https://arxiv.org/abs/fake_{random.randint(1000,9999)}"
        })
        
    # Inject Relationships
    with client.driver.session() as session:
        for chunk in [relationships[i:i + 200] for i in range(0, len(relationships), 200)]:
            session.run("""
                UNWIND $rels AS rel
                MATCH (s:Entity {name: rel.source})
                MATCH (t:Entity {name: rel.target})
                MERGE (s)-[r:RELATIONSHIP {predicate: rel.predicate}]->(t)
                SET r.confidence = rel.confidence,
                    r.source_url = rel.source_url,
                    r.created_at = datetime() - duration('P' + toInteger(rand() * 60) + 'D')
            """, rels=chunk)
            
    # Calculate degree centrality to set 'degree' property and identify hubs
    print("🕸️ Calculating graph metrics...")
    with client.driver.session() as session:
        session.run("""
            MATCH (n:Entity)
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) AS degree
            SET n.degree = degree
        """)
        
    print("✅ Demo Dataset seeded successfully!")
    print("   Entities: ~550")
    print("   Relationships: ~2200")
    
if __name__ == "__main__":
    seed_demo_dataset()
