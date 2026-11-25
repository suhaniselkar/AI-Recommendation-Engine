
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class RecommendationEngine:

    def __init__(self, products: pd.DataFrame, interactions: pd.DataFrame):

        self.products = products.copy().fillna("")
        self.interactions = interactions.copy()

        # Ensure required product columns exist
        required_columns = [
            "product_id",
            "title",
            "category",
            "description",
            "tags"
        ]

        for column in required_columns:
            if column not in self.products.columns:
                self.products[column] = ""

        # Convert text columns safely
        for column in ["title", "category", "description", "tags"]:
            self.products[column] = (
                self.products[column].astype(str)
            )

        # Build product text
        self.products["text"] = (
            self.products["title"] + " " +
            self.products["category"] + " " +
            self.products["description"] + " " +
            self.products["tags"]
        ).str.lower().str.strip()

        self.product_ids = self.products["product_id"].tolist()

        self.id_to_idx = {
            product_id: index
            for index, product_id in enumerate(self.product_ids)
        }

        # Build TF-IDF matrix safely
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2)
        )

        self.content_matrix = None

        if not self.products.empty:
            try:
                self.content_matrix = self.vectorizer.fit_transform(
                    self.products["text"]
                )
            except ValueError:
                # Handles empty vocabulary
                self.content_matrix = None

        self._build_collaborative()

    # ==========================================
    # COLLABORATIVE FILTERING
    # ==========================================

    def _build_collaborative(self):

        if self.interactions.empty:

            self.user_item = pd.DataFrame()
            self.user_similarity = np.zeros((0, 0))

            return

        weights = {
            "view": 1.0,
            "click": 2.0,
            "cart": 3.0,
            "purchase": 4.0,
            "like": 3.0
        }

        data = self.interactions.copy()

        data["weight"] = (
            data["event_type"]
            .map(weights)
            .fillna(1.0)
        )

        if "rating" in data.columns:

            data["weight"] = (
                data["weight"] *
                (
                    pd.to_numeric(
                        data["rating"],
                        errors="coerce"
                    )
                    .fillna(3)
                    .clip(1, 5) / 3.0
                )
            )

        self.user_item = data.pivot_table(
            index="user_id",
            columns="product_id",
            values="weight",
            aggfunc="sum",
            fill_value=0
        )

        user_matrix = self.user_item.to_numpy(
            dtype=np.float64
        )

        if user_matrix.size == 0:
            self.user_similarity = np.zeros(
                (len(self.user_item.index),) * 2,
                dtype=np.float64
            )
            return

        self.user_similarity = cosine_similarity(
            user_matrix
        )

        self.user_similarity = np.asarray(
            self.user_similarity,
            dtype=np.float64
        )

    # ==========================================
    # CONTENT-BASED FILTERING
    # ==========================================

    def _content_scores(self, user_id):

        scores = np.zeros(
            len(self.products),
            dtype=np.float64
        )

        if (
            self.content_matrix is None or
            self.products.empty or
            self.interactions.empty
        ):
            return scores

        user_rows = self.interactions[
            self.interactions["user_id"] == user_id
        ]

        if user_rows.empty:
            return scores

        # Identify positive user interactions
        liked = user_rows[
            user_rows["event_type"].isin(
                ["purchase", "like", "cart"]
            )
        ].copy()

        # Include highly rated products
        if "rating" in user_rows.columns:

            ratings = pd.to_numeric(
                user_rows["rating"],
                errors="coerce"
            ).fillna(0)

            high_rated = user_rows[ratings >= 4]

            liked = pd.concat(
                [liked, high_rated]
            ).drop_duplicates()

        if liked.empty:
            liked = user_rows

        # Get valid product indexes
        indices = [
            self.id_to_idx[product_id]
            for product_id in liked["product_id"]
            if product_id in self.id_to_idx
        ]

        if not indices:
            return scores

        # Calculate user preference profile
        profile = np.asarray(
            self.content_matrix[indices].mean(axis=0),
            dtype=np.float64
        ).reshape(1, -1)

        # Calculate content similarity
        scores = cosine_similarity(
            profile,
            self.content_matrix
        ).ravel()

        return np.asarray(
            scores,
            dtype=np.float64
        )

    # ==========================================
    # COLLABORATIVE SCORES
    # ==========================================

    def _collab_scores(self, user_id):

        scores = np.zeros(
            len(self.products),
            dtype=np.float64
        )

        if (
            self.user_item.empty or
            user_id not in self.user_item.index
        ):
            return scores

        user_index = list(
            self.user_item.index
        ).index(user_id)

        similarities = np.asarray(
            self.user_similarity[user_index],
            dtype=np.float64
        ).copy()

        # Exclude current user
        similarities[user_index] = 0

        if similarities.sum() <= 0:
            return scores

        user_matrix = self.user_item.to_numpy(
            dtype=np.float64
        )

        weighted_scores = np.dot(
            similarities,
            user_matrix
        )

        scores = pd.Series(
            weighted_scores,
            index=self.user_item.columns
        ).reindex(
            self.product_ids,
            fill_value=0
        ).to_numpy(
            dtype=np.float64
        )

        max_score = scores.max()

        return (
            scores / max_score
            if max_score > 0
            else scores
        )

    # ==========================================
    # MAIN RECOMMENDATION FUNCTION
    # ==========================================

    def recommend(
        self,
        user_id,
        limit=5,
        method="hybrid",
        category=None
    ):

        limit = max(1, int(limit))

        content = self._content_scores(user_id)

        collaborative = self._collab_scores(user_id)

        # Popularity scores
        if (
            self.interactions.empty or
            "product_id" not in self.interactions.columns
        ):
            popular = np.zeros(
                len(self.products),
                dtype=np.float64
            )
        else:
            popular = (
                self.interactions
                .groupby("product_id")
                .size()
                .reindex(
                    self.product_ids,
                    fill_value=0
                )
                .to_numpy(dtype=np.float64)
            )

        max_popular = (
            popular.max()
            if len(popular) > 0
            else 0
        )

        if max_popular > 0:
            popular = popular / max_popular

        # Select recommendation method
        if method == "content":

            final_scores = content

        elif method == "collaborative":

            final_scores = collaborative

        elif method == "popular":

            final_scores = popular

        else:

            final_scores = (
                0.45 * content +
                0.45 * collaborative +
                0.10 * popular
            )

        # Exclude products already interacted with
        if (
            not self.interactions.empty and
            "user_id" in self.interactions.columns and
            "product_id" in self.interactions.columns
        ):
            seen = set(
                self.interactions.loc[
                    self.interactions["user_id"] == user_id,
                    "product_id"
                ].tolist()
            )
        else:
            seen = set()

        result = self.products.copy()

        result["score"] = final_scores
        result["content_score"] = content
        result["collaborative_score"] = collaborative
        result["popularity_score"] = popular

        result = result[
            ~result["product_id"].isin(seen)
        ]

        # Category filtering
        if category and str(category).lower() != "all":

            result = result[
                result["category"].astype(str).str.lower()
                == str(category).lower()
            ]

        # Sort and select recommendations
        result = result.sort_values(
            ["score", "title"],
            ascending=[False, True]
        ).head(limit)

        return result.drop(
            columns=["text"],
            errors="ignore"
        ).to_dict(orient="records")

    # ==========================================
    # MODEL METRICS
    # ==========================================

    def metrics(self):

        return {
            "users": int(
                self.interactions["user_id"].nunique()
                if "user_id" in self.interactions.columns
                else 0
            ),

            "products": int(
                len(self.products)
            ),

            "interactions": int(
                len(self.interactions)
            ),

            "categories": int(
                self.products["category"].nunique()
            )
        }
