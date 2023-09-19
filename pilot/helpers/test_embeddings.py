from .embeddings import distances_from_embeddings, closest_items


def test_distances_from_embeddings_cosine():
    # Given
    query_emb = [0.1, 0.2, 0.3, 0.4]
    embeddings_list = [
        [0.5, 0.6, 0.7, 0.8],
        [0.9, 1.0, 1.1, 1.2],
        [0.11, 0.19, 0.34, 0.43],
        [0.2, 0.1, 0.4, 0.3]
    ]

    # When
    distances = distances_from_embeddings(query_emb, embeddings_list, distance_metric="cosine")

    # Then
    assert distances == [0.031136068373033732, 0.049034791329543914, 0.001343986985706369, 0.06666666666666687]


def test_closest_items_cosine():
    # Given
    query_emb = [0.1, 0.2, 0.3, 0.4]
    embeddings_list = [
        {'name': 'A', 'embedding': [0.5, 0.6, 0.7, 0.8]},
        {'name': 'B', 'embedding': [0.9, 1.0, 1.1, 1.2]},
        {'name': 'C', 'embedding': [0.11, 0.19, 0.34, 0.43]},
        {'name': 'D', 'embedding': [0.2, 0.1, 0.4, 0.3]},
    ]

    # When
    top_items = closest_items(query_emb, embeddings_list, top_n=2, distance_metric="cosine")

    # Then
    assert top_items[0]['name'] == 'C'
    assert top_items[1]['name'] == 'A'


# def test_closest_items_dot():
#     # Given
#     query_emb = [0.1, 0.2, 0.3, 0.4]
#     embeddings_list = [
#         {'name': 'A', 'embedding': [0.5, 0.6, 0.7, 0.8]},
#         {'name': 'B', 'embedding': [0.9, 1.0, 1.1, 1.2]},
#         {'name': 'C', 'embedding': [0.11, 0.19, 0.34, 0.43]},
#         {'name': 'D', 'embedding': [0.2, 0.1, 0.4, 0.3]},
#     ]
#
#     # When
#     top_items = closest_items(query_emb, embeddings_list, top_n=2, distance_metric="dot")
#
#     # Then
#     assert top_items[0]['name'] == 'C'
#     assert top_items[1]['name'] == 'A'
