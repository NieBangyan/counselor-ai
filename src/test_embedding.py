import numpy as np

embeddings = np.load("storage/embeddings/handbook_embeddings.npy")

print("Shape:", embeddings.shape)
print("Data type:", embeddings.dtype)

print("\nFirst vector (first 10 dimensions):")
print(embeddings[0][:10])