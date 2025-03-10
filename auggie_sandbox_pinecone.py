# -*- coding: utf-8 -*-
"""Auggie-Sandbox-Pinecone.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1ALBZ_x8aWYsRnOb4tKsvNqUt9CVI8dN0
"""

!pip install scikit-learn pinecone-client sentence-transformers faiss-cpu transformers matplotlib networkx

# Import necessary libraries:
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import faiss
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import re
import torch
from sklearn.preprocessing import normalize

PINECONE_API_KEY = 'API_KEY' # Replace with your API key
PINECONE_ENV = 'ENV_NAME'  # Replace with your environment name if necessary

# Initialize Pinecone client
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(
    api_key=PINECONE_API_KEY
)

# Check if your desired index (auggie-transcripts) exists, or create it if necessary
if 'auggie-colab' not in pc.list_indexes().names():
    pc.create_index(
        name='auggie-colab',
        dimension=384,
        metric='euclidean',
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )

# Connect to the desired index
index = pc.Index('auggie-colab')

# Example to use the index: Get information about the index
print(index.describe_index_stats())

# Create an instance of the embedding model
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

dummy_data = [
    # Symptoms
    {"id": "symptom_1", "values": model.encode("fever").tolist(), "metadata": {"category": "symptom", "description": "fever"}},
    {"id": "symptom_2", "values": model.encode("headache").tolist(), "metadata": {"category": "symptom", "description": "headache"}},
    {"id": "symptom_3", "values": model.encode("nausea").tolist(), "metadata": {"category": "symptom", "description": "nausea"}},
    {"id": "symptom_4", "values": model.encode("cough").tolist(), "metadata": {"category": "symptom", "description": "cough"}},
    {"id": "symptom_5", "values": model.encode("fatigue").tolist(), "metadata": {"category": "symptom", "description": "fatigue"}},
    {"id": "symptom_6", "values": model.encode("shortness of breath").tolist(), "metadata": {"category": "symptom", "description": "shortness of breath"}},
    {"id": "symptom_7", "values": model.encode("sore throat").tolist(), "metadata": {"category": "symptom", "description": "sore throat"}},

    # Diagnostics
    {"id": "diagnostic_1", "values": model.encode("influenza").tolist(), "metadata": {"category": "diagnostic", "description": "influenza"}},
    {"id": "diagnostic_2", "values": model.encode("migraine").tolist(), "metadata": {"category": "diagnostic", "description": "migraine"}},
    {"id": "diagnostic_3", "values": model.encode("COVID-19").tolist(), "metadata": {"category": "diagnostic", "description": "COVID-19"}},
    {"id": "diagnostic_4", "values": model.encode("gastroenteritis").tolist(), "metadata": {"category": "diagnostic", "description": "gastroenteritis"}},
    {"id": "diagnostic_5", "values": model.encode("asthma").tolist(), "metadata": {"category": "diagnostic", "description": "asthma"}},
    {"id": "diagnostic_6", "values": model.encode("pneumonia").tolist(), "metadata": {"category": "diagnostic", "description": "pneumonia"}},
    {"id": "diagnostic_7", "values": model.encode("tonsillitis").tolist(), "metadata": {"category": "diagnostic", "description": "tonsillitis"}},

    # Treatments
    {"id": "treatment_1", "values": model.encode("antiviral therapy").tolist(), "metadata": {"category": "treatment", "description": "antiviral therapy"}},
    {"id": "treatment_2", "values": model.encode("pain relievers").tolist(), "metadata": {"category": "treatment", "description": "pain relievers"}},
    {"id": "treatment_3", "values": model.encode("rehydration").tolist(), "metadata": {"category": "treatment", "description": "rehydration"}},
    {"id": "treatment_4", "values": model.encode("bronchodilator inhaler").tolist(), "metadata": {"category": "treatment", "description": "bronchodilator inhaler"}},
    {"id": "treatment_5", "values": model.encode("antibiotics").tolist(), "metadata": {"category": "treatment", "description": "antibiotics"}},
    {"id": "treatment_6", "values": model.encode("corticosteroids").tolist(), "metadata": {"category": "treatment", "description": "corticosteroids"}},
    {"id": "treatment_7", "values": model.encode("antihistamines").tolist(), "metadata": {"category": "treatment", "description": "antihistamines"}},
]

# Insert the extended dummy data into the Pinecone index
index.upsert(vectors=dummy_data)

# Function to fetch data from Pinecone index
def fetch_pinecone_data(index, query_text, namespace=None, top_k=50):
    vector = model.encode([query_text])[0]  # Create embedding for the query
    vector = vector.tolist()  # Convert NumPy array to list for Pinecone compatibility
    result = index.query(
        vector=vector,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True
    )
    return result

# Initialize the embedding model and NER pipeline
device = 0 if torch.cuda.is_available() else -1
ner_pipeline = pipeline("token-classification", model="blaze999/Medical-NER", device=device)

# Example query to test data fetching
test_query = "The patient has fever and nausea, diagnosed with influenza, and undergoing antiviral therapy."
entities = ner_pipeline(test_query)

# Process entities to extract symptoms, diagnostics, and treatments
relationships = {
    "symptoms": [entity['word'].replace('▁', '').strip() for entity in entities if 'SIGN_SYMPTOM' in entity['entity']],
    "diagnostics": [entity['word'].replace('▁', '').strip() for entity in entities if 'DISEASE_DISORDER' in entity['entity']],
    "treatments": []
}

current_treatment = ''
for entity in entities:
    if 'MEDICATION' in entity['entity']:
        current_treatment += entity['word'].replace('▁', '').strip() + ' '
    else:
        if current_treatment:
            relationships["treatments"].append(current_treatment.strip())
            current_treatment = ''
if current_treatment:
    relationships["treatments"].append(current_treatment.strip())

# Print extracted information
print("\nExtracted Symptoms:")
for symptom in relationships["symptoms"]:
    print(f"- {symptom}")

print("\nExtracted Diagnostics:")
for diagnostic in relationships["diagnostics"]:
    print(f"- {diagnostic}")

print("\nExtracted Treatments:")
for treatment in relationships["treatments"]:
    print(f"+ {treatment}")

# Fetch relevant data from Pinecone index using one of the extracted symptoms
if relationships["symptoms"]:
    pinecone_results = fetch_pinecone_data(index, relationships["symptoms"][0], top_k=10)

    # Process Pinecone results to update relationships
    for match in pinecone_results['matches']:
        metadata = match['metadata']
        category = metadata.get('category', '')
        description = metadata.get('description', '')

        if category == 'symptom':
            relationships["symptoms"].append(description)
        elif category == 'diagnostic':
            relationships["diagnostics"].append(description)
        elif category == 'treatment':
            relationships["treatments"].append(description)

# Remove duplicates
for key in relationships:
    relationships[key] = list(set(relationships[key]))

# Set up FAISS index with L2 distance metric for diagnostics
if relationships["diagnostics"]:
    diagnostic_embeddings = model.encode(relationships["diagnostics"])
    normalized_embeddings = normalize(diagnostic_embeddings, norm='l2')
    dimension = normalized_embeddings.shape[1]

    faiss_index = faiss.IndexFlatL2(dimension)
    faiss_index.add(np.array(normalized_embeddings))

    # Perform FAISS similarity search with the user's symptom query embedding
    query_embedding = model.encode([test_query])
    normalized_query_embedding = normalize(query_embedding, norm='l2')

    k = 5  # Number of top results
    distances, indices = faiss_index.search(normalized_query_embedding, k)

    # Collect top diagnostics based on similarity search
    top_diagnostics = []
    if len(indices[0]) > 0:
        for i, idx in enumerate(indices[0]):
            diagnostic = relationships["diagnostics"][idx]
            distance = distances[0][i]
            top_diagnostics.append((diagnostic, distance))
else:
    top_diagnostics = []

# Consolidated display of all results
print("\nSymptoms:")
if relationships["symptoms"]:
    for symptom in relationships["symptoms"]:
        print(f"- {symptom}")
else:
    print("No symptoms extracted.")

print("\nTop Diagnostics:")
if top_diagnostics:
    for i, (diagnostic, distance) in enumerate(top_diagnostics):
        # Adjusting the distance to resemble your previous output
        scaled_distance = distance * 100  # Scale the distance to a larger value
        print(f"{i+1}. {diagnostic} (Distance: {scaled_distance:.2f})")
else:
    print("No diagnostics found.")

print("\nTreatments:")
if relationships["treatments"]:
    for treatment in relationships["treatments"]:
        print(f"+ {treatment}")
else:
    print("No treatments extracted.")

# Generate graph
def generate_graph(relationships, top_diagnostics):
    G = nx.DiGraph()

    # Add nodes for symptoms, diagnostics, and treatments:
    for symptom in relationships["symptoms"]:
        G.add_node(symptom, type="symptom", color="blue")

    for diagnostic, _ in top_diagnostics:
        G.add_node(diagnostic, type="diagnostic", color="red")

    for treatment in relationships["treatments"]:
        G.add_node(treatment, type="treatment", color="green")

    # Normalize distances for better visualization of edge thickness
    max_distance = max([distance for _, distance in top_diagnostics]) if top_diagnostics else 1
    min_distance = min([distance for _, distance in top_diagnostics]) if top_diagnostics else 0

    def normalize_distance(distance):
        if max_distance - min_distance == 0:
            return 1
        return 0.5 + 2.5 * ((distance - min_distance) / (max_distance - min_distance))

    # Add edges between symptoms and diagnostics using normalized FAISS distances as weights
    for diagnostic, distance in top_diagnostics:
        normalized_weight = normalize_distance(distance)
        for symptom in relationships["symptoms"]:
            G.add_edge(symptom, diagnostic, weight=normalized_weight)

    # Add edges between diagnostics and treatments
    for diagnostic, _ in top_diagnostics:
        for treatment in relationships["treatments"]:
            G.add_edge(diagnostic, treatment, weight=1.0)

    # Generate the graph layout
    pos = nx.spring_layout(G, k=2.0, iterations=50, seed=42)  # Increased k to spread nodes more effectively

    # Plot the graph
    plt.figure(figsize=(16, 12))
    edge_weights = [G[u][v]['weight'] for u, v in G.edges]
    node_colors = [G.nodes[node].get('color', 'lightgray') for node in G.nodes]

    nx.draw(
        G, pos, with_labels=True,
        node_color=node_colors,
        edge_color='gray', font_size=10, node_size=4500, font_weight="bold", arrows=True,
        width=edge_weights, alpha=0.9, connectionstyle="arc3,rad=0.2"  # Add some curvature to edges
    )

    plt.title("Relationship Graph: Symptoms, Diagnostics, and Treatments")
    plt.axis("off")
    plt.show()

# Generate and display the graph
generate_graph(relationships, top_diagnostics)