import pickle
import numpy as np


def cosine_distance(v1, v2):
    """
    Compute the cosine distance between two vectors.
    Cosine distance is defined as 1.0 minus the cosine similarity.
    """
    # Normalize the vectors (make them unit vectors)
    norm_v1 = v1 / np.linalg.norm(v1)
    norm_v2 = v2 / np.linalg.norm(v2)

    # Compute the cosine similarity
    cosine_similarity = np.dot(norm_v1, norm_v2)

    # Convert the cosine similarity to cosine distance
    distance = 1.0 - cosine_similarity

    return distance


# def dot_product_distance(v1, v2):
#     # return v1 @ v2
#     return np.dot(v1, v2)


def closest_items(query_embedding, items, top_n=5, distance_metric="cosine"):
    """
    Find the N closest items based on their embeddings.

    Args:
    - query_embedding (list of float): The embedding of the query item.
    - items (list of dict): A list of items where each item has an 'embedding' key with its embedding.
    - N (int): The number of closest items to return.

    Returns:
    - list of dict: The N closest items based on embeddings.
    """
    distance_function = _get_distance_function(distance_metric)

    distances = [(item, distance_function(query_embedding, item['embedding'])) for item in items]

    sorted_items = sorted(distances, key=lambda x: x[1])
    # sorted_items = sorted(distances, key=lambda x: (x[1], -x[0]['data']['stars']))

    return [item[0]['data'] for item in sorted_items[:top_n]]
    # result = []
    # for item, distance in sorted_items[:top_n]:
    #     item_copy = item.copy()
    #     del item_copy['embedding']
    #     item_copy['distance'] = distance
    #     result.append(item_copy)
    #
    # return result


def distances_from_embeddings(query_embedding, embeddings, distance_metric="cosine"):
    """
    Compute distances between a query embedding and a list of embeddings.

    Args:
    - query_embedding (list of float): The query embedding.
    - embeddings (list of list of float): A list of embeddings to compute distances to.
    - distance_metric (str): The distance metric to use. Currently only "cosine" is supported.

    Returns:
    - list of float: List of computed distances.
    """
    distance_function = _get_distance_function(distance_metric)

    distances = [distance_function(query_embedding, emb) for emb in embeddings]

    return distances


def _get_distance_function(distance_metric: str):
    if distance_metric == "cosine":
        return cosine_distance
    # if distance_metric == "dot":
    #     return dot_product_distance
    else:
        raise ValueError(f"Unsupported distance metric: {distance_metric}")


def save_embeddings_to_file(embeddings, filename):
    """
    Save the embeddings to a file.

    Args:
    - embeddings (list of dict): List of embeddings with repository details.
    - filename (str): Path to the file where embeddings should be saved.
    """
    with open(filename, 'wb') as f:
        pickle.dump(embeddings, f)


def load_embeddings_from_file(filename):
    """
    Load the embeddings from a file.

    Args:
    - filename (str): Path to the file from which embeddings should be loaded.

    Returns:
    - list of dict: List of loaded embeddings with repository details.
    """
    with open(filename, 'rb') as f:
        return pickle.load(f)