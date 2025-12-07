import requests

response = requests.get('http://localhost:8000/api/cases/1db290e3/documents')
data = response.json()

print(f"Total: {data['total']}")
print(f"\nDerniers 5 documents:")
for doc in data['documents'][:5]:
    print(f"  - {doc['nom_fichier']} | source_type: {doc.get('source_type')} | case_id: {doc['case_id']}")