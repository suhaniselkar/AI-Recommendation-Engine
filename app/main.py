
from pathlib import Path
import hashlib
import hmac
import secrets
import uuid
import sqlite3
import pandas as pd
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .data import ensure_demo_data, PRODUCTS_PATH, INTERACTIONS_PATH
from .database import (
    save_interaction,
    create_customer,
    find_customer_by_email,
    create_session,
    find_session,
    delete_session,
    get_customer_by_id,
    update_customer_profile,
    update_customer_password,
    get_customer_interactions,
    delete_customer_sessions,
    add_to_wishlist,
    get_customer_wishlist,
    remove_from_wishlist,
    add_to_cart,
    get_customer_cart,
    update_cart_quantity,
    remove_from_cart,
    clear_customer_cart,
    create_order,
    get_customer_orders,
    get_order_by_id,
    cancel_customer_order,
)
from .recommender import RecommendationEngine
# ==========================================
# INITIALIZATION
# ==========================================
ensure_demo_data()
products = pd.read_csv(PRODUCTS_PATH)
interactions = pd.read_csv(INTERACTIONS_PATH)
engine = RecommendationEngine(products, interactions)
app = FastAPI(
    title="AI Recommendation Engine",
    version="1.3.0",
    description="Hybrid recommender with authentication, customer profiles, wishlist and shopping cart management",
)
STATIC = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# ==========================================
# PYDANTIC MODELS
# ==========================================
class InteractionIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=80)
    product_id: str = Field(min_length=1, max_length=50)
    event_type: str = Field(
        default="view",
        pattern="^(view|click|cart|purchase|like)$"
    )
    rating: int | None = Field(default=None, ge=1, le=5)
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=EMAIL_PATTERN
    )
    password: str = Field(min_length=8, max_length=128)
class LoginIn(BaseModel):
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=EMAIL_PATTERN
    )
    password: str = Field(min_length=8, max_length=128)
class ProfileUpdateIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=EMAIL_PATTERN
    )
class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
class WishlistIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=50)
class CartIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=50)
    quantity: int = Field(default=1, ge=1, le=100)
class CartQuantityUpdateIn(BaseModel):
    quantity: int = Field(ge=1, le=100)
# ==========================================
# PASSWORD FUNCTIONS
# ==========================================
def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        310000
    )
    return salt.hex() + ":" + digest.hex()
def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            310000
        ).hex()
        return hmac.compare_digest(expected, digest_hex)
    except (ValueError, TypeError):
        return False
# ==========================================
# CUSTOMER AUTHENTICATION HELPERS
# ==========================================
def public_customer(user):
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"]
    }
def issue_session(user):
    token = secrets.token_urlsafe(36)
    create_session(token, user["user_id"])
    return {
        "token": token,
        "customer": public_customer(user)
    }
def current_customer(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Please sign in"
        )
    user = find_session(authorization[7:].strip())
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please sign in again."
        )
    return user
# ==========================================
# PRODUCT HELPER
# ==========================================
def find_product(product_id):
    matches = products[
        products["product_id"].astype(str) == str(product_id)
    ]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()
# ==========================================
# HOME AND HEALTH
# ==========================================
@app.get("/", response_class=HTMLResponse)
def home():
    return (STATIC / "index.html").read_text(encoding="utf-8")
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AI Recommendation Engine"
    }
# ==========================================
# AUTHENTICATION APIs
# ==========================================
@app.post("/api/auth/register")
def register(payload: RegisterIn):
    email = payload.email.lower().strip()
    if find_customer_by_email(email):
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists."
        )
    user = {
        "user_id": "USR_" + uuid.uuid4().hex[:12].upper(),
        "name": payload.name.strip(),
        "email": email,
        "password_hash": hash_password(payload.password)
    }
    try:
        create_customer(
            user["user_id"],
            user["name"],
            user["email"],
            user["password_hash"]
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="This email is already registered."
        )
    return issue_session(user)
@app.post("/api/auth/login")
def login(payload: LoginIn):
    user = find_customer_by_email(
        payload.email.lower().strip()
    )
    if not user or not verify_password(
        payload.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )
    return issue_session(user)
@app.get("/api/auth/me")
def auth_me(
    authorization: str | None = Header(default=None)
):
    return {
        "customer": public_customer(
            current_customer(authorization)
        )
    }
@app.post("/api/auth/logout")
def auth_logout(
    authorization: str | None = Header(default=None)
):
    if authorization and authorization.startswith("Bearer "):
        delete_session(authorization[7:].strip())
    return {"message": "Signed out"}
# ==========================================
# CUSTOMER PROFILE APIs
# ==========================================
@app.get("/api/customer/profile")
def customer_profile(
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    profile = get_customer_by_id(user["user_id"])
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Customer profile not found"
        )
    return {"profile": profile}
@app.patch("/api/customer/profile")
def edit_customer_profile(
    payload: ProfileUpdateIn,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    name = payload.name.strip()
    email = payload.email.lower().strip()
    existing = find_customer_by_email(email)
    if existing and existing["user_id"] != user["user_id"]:
        raise HTTPException(
            status_code=409,
            detail="This email is already used by another account."
        )
    try:
        updated = update_customer_profile(
            user["user_id"],
            name,
            email
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="This email is already used by another account."
        )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Customer profile not found"
        )
    return {
        "message": "Profile updated successfully",
        "profile": updated
    }
# ==========================================
# CUSTOMER PASSWORD API
# ==========================================
@app.put("/api/customer/password")
def change_customer_password(
    payload: PasswordChangeIn,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    stored_user = find_customer_by_email(user["email"])
    if not stored_user or not verify_password(
        payload.current_password,
        stored_user["password_hash"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect."
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password."
        )
    update_customer_password(
        user["user_id"],
        hash_password(payload.new_password)
    )
    delete_customer_sessions(user["user_id"])
    return {
        "message": "Password changed successfully. Please sign in again."
    }
# ==========================================
# CUSTOMER INTERACTION HISTORY
# ==========================================
@app.get("/api/customer/history")
def customer_history(
    limit: int = 50,
    authorization: str | None = Header(default=None)
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100"
        )
    user = current_customer(authorization)
    history = get_customer_interactions(
        user["user_id"],
        limit
    )
    product_lookup = {
        str(row["product_id"]): str(row["title"])
        for _, row in products.iterrows()
    }
    for item in history:
        item["product_title"] = product_lookup.get(
            str(item["product_id"]),
            "Unknown product"
        )
    return {
        "user_id": user["user_id"],
        "count": len(history),
        "history": history
    }
# ==========================================
# WISHLIST APIs
# ==========================================
@app.post("/api/wishlist")
def add_wishlist_item(
    payload: WishlistIn,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    product = find_product(payload.product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    added = add_to_wishlist(
        user["user_id"],
        payload.product_id
    )
    if not added:
        return {
            "message": "Product is already in your wishlist",
            "added": False,
            "product_id": payload.product_id
        }
    return {
        "message": "Product added to wishlist successfully",
        "added": True,
        "product": product
    }
@app.get("/api/wishlist")
def view_wishlist(
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    wishlist = get_customer_wishlist(user["user_id"])
    items = []
    for item in wishlist:
        product = find_product(item["product_id"])
        items.append({
            **item,
            "product": product
        })
    return {
        "user_id": user["user_id"],
        "count": len(items),
        "wishlist": items
    }
@app.delete("/api/wishlist/{product_id}")
def delete_wishlist_item(
    product_id: str,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    removed = remove_from_wishlist(
        user["user_id"],
        product_id
    )
    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Product not found in your wishlist"
        )
    return {
        "message": "Product removed from wishlist successfully",
        "removed": True,
        "product_id": product_id
    }
# ==========================================
# SHOPPING CART APIs
# ==========================================
@app.post("/api/cart")
def add_cart_item(
    payload: CartIn,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    product = find_product(payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    add_to_cart(
        user["user_id"],
        payload.product_id,
        payload.quantity
    )
    return {
        "message": "Product added to cart successfully",
        "product_id": payload.product_id,
        "quantity_added": payload.quantity
    }
@app.get("/api/cart")
def view_cart(
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    cart = get_customer_cart(user["user_id"])
    items = []
    subtotal = 0.0
    for item in cart:
        product = find_product(item["product_id"])
        if not product:
            continue
        try:
            price = float(product.get("price", 0))
        except (TypeError, ValueError):
            price = 0.0
        item_total = price * item["quantity"]
        subtotal += item_total
        items.append({
            **item,
            "product": product,
            "unit_price": price,
            "item_total": round(item_total, 2)
        })
    return {
        "user_id": user["user_id"],
        "total_items": sum(item["quantity"] for item in items),
        "unique_products": len(items),
        "subtotal": round(subtotal, 2),
        "cart": items
    }
@app.patch("/api/cart/{product_id}")
def edit_cart_quantity(
    product_id: str,
    payload: CartQuantityUpdateIn,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    product = find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updated = update_cart_quantity(
        user["user_id"],
        product_id,
        payload.quantity
    )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Product not found in your cart"
        )
    return {
        "message": "Cart quantity updated successfully",
        "product_id": product_id,
        "quantity": payload.quantity
    }
@app.delete("/api/cart/{product_id}")
def delete_cart_item(
    product_id: str,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    removed = remove_from_cart(user["user_id"], product_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Product not found in your cart"
        )
    return {
        "message": "Product removed from cart successfully",
        "removed": True,
        "product_id": product_id
    }
@app.delete("/api/cart")
def delete_entire_cart(
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    clear_customer_cart(user["user_id"])
    return {
        "message": "Shopping cart cleared successfully"
    }
@app.get("/api/categories")
def categories():
    return sorted(products.category.unique().tolist())
@app.get("/api/users")
def users():
    return sorted(interactions.user_id.unique().tolist())
# ==========================================
# RECOMMENDATION API
# ==========================================
# IMPORTANT: Keep /me route before /{user_id}
@app.get("/api/recommendations/me")
def my_recommendations(
    limit: int = 10,
    method: str = "hybrid",
    category: str | None = None,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 50"
        )
    if method not in {"hybrid", "content", "collaborative", "popular"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid recommendation method"
        )
    results = engine.recommend(
        user["user_id"],
        limit,
        method,
        category
    )
    return {
        "user_id": user["user_id"],
        "method": method,
        "count": len(results),
        "recommendations": results
    }
@app.get("/api/recommendations/{user_id}")
def recommendations(
    user_id: str,
    limit: int = 10,
    method: str = "hybrid",
    category: str | None = None
):
    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 50"
        )
    if method not in {"hybrid", "content", "collaborative", "popular"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid recommendation method"
        )
    results = engine.recommend(
        user_id,
        limit,
        method,
        category
    )
    return {
        "user_id": user_id,
        "method": method,
        "count": len(results),
        "recommendations": results
    }
@app.get("/api/recommendations/{user_id}/preferences")
def customer_preferences(user_id: str):
    preferences = engine.user_preferences(user_id)
    return {
        "user_id": user_id,
        "preferences": preferences
    }
@app.get("/api/products/{product_id}/similar")
def similar_products(
    product_id: str,
    limit: int = 5
):
    if limit < 1 or limit > 20:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 20"
        )
    product = find_product(product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    results = engine.similar_products(product_id, limit)
    return {
        "product_id": product_id,
        "count": len(results),
        "similar_products": results
    }
# ==========================================
# PRODUCT MANAGEMENT APIs
# ==========================================
@app.get("/api/products")
def list_products(
    category: str | None = None,
    search: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort_by: str = "title",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 10
):
    df = products.copy()
    # Ensure price column exists
    if "price" not in df.columns:
        df["price"] = 0.0
    df["price"] = pd.to_numeric(
        df["price"], errors="coerce"
    ).fillna(0.0)
    # Category filter
    if category and category.lower() != "all":
        df = df[
            df["category"].astype(str).str.lower()
            == category.strip().lower()
        ]
    # Search title and description
    if search and search.strip():
        term = search.strip()
        title_match = df["title"].astype(str).str.contains(
            term, case=False, na=False, regex=False
        )
        description_match = df["description"].astype(str).str.contains(
            term, case=False, na=False, regex=False
        )
        df = df[title_match | description_match]
    # Minimum price
    if min_price is not None:
        if min_price < 0:
            raise HTTPException(
                status_code=400,
                detail="min_price cannot be negative"
            )
        df = df[df["price"] >= min_price]
    # Maximum price
    if max_price is not None:
        if max_price < 0:
            raise HTTPException(
                status_code=400,
                detail="max_price cannot be negative"
            )
        df = df[df["price"] <= max_price]
    if min_price is not None and max_price is not None:
        if min_price > max_price:
            raise HTTPException(
                status_code=400,
                detail="min_price cannot exceed max_price"
            )
    # Sorting
    allowed_sort_fields = {
        "title", "price", "category", "product_id"
    }
    if sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=400,
            detail="sort_by must be title, price, category, or product_id"
        )
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(
            status_code=400,
            detail="sort_order must be asc or desc"
        )
    df = df.sort_values(
        by=sort_by,
        ascending=(sort_order == "asc"),
        kind="stable"
    )
    # Pagination validation
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="page must be at least 1"
        )
    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="page_size must be between 1 and 100"
        )
    total_products = len(df)
    total_pages = (
        (total_products + page_size - 1) // page_size
    )
    start = (page - 1) * page_size
    end = start + page_size
    paginated_products = df.iloc[start:end].to_dict(
        orient="records"
    )
    return {
        "total_products": total_products,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "products": paginated_products
    }
# ==========================================
# PRODUCT DETAILS API
# ==========================================
@app.get("/api/products/{product_id}")
def get_product_details(product_id: str):
    product = find_product(product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    return {
        "message": "Product details retrieved successfully",
        "product": product
    }
# ==========================================
# CUSTOMER BEHAVIOUR TRACKING
# ==========================================
@app.post("/api/interactions")
def create_interaction(
    payload: InteractionIn,
    authorization: str | None = Header(default=None)
):
    # Verify logged-in customer
    user = current_customer(authorization)
    # Prevent users from recording activity for another customer
    if payload.user_id != user["user_id"]:
        raise HTTPException(
            status_code=403,
            detail="You can only track your own activities"
        )
    # Verify product
    product = find_product(payload.product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    # Save interaction in SQLite
    save_interaction(
        user["user_id"],
        payload.product_id,
        payload.event_type,
        payload.rating
    )
    # Refresh recommendation engine data
    global interactions, engine
    new = pd.DataFrame([{
        "user_id": user["user_id"],
        "product_id": payload.product_id,
        "event_type": payload.event_type,
        "rating": payload.rating
    }])
    interactions = pd.concat(
        [interactions, new],
        ignore_index=True
    )
    engine = RecommendationEngine(
        products,
        interactions
    )
    return {
        "message": "Customer activity tracked successfully",
        "user_id": user["user_id"],
        "product_id": payload.product_id,
        "event_type": payload.event_type,
        "recommendation_model": "refreshed"
    }
@app.get("/api/customer/behavior-summary")
def customer_behavior_summary(
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    history = get_customer_interactions(
        user["user_id"],
        1000
    )
    event_counts = {}
    category_counts = {}
    for item in history:
        event = item["event_type"]
        event_counts[event] = (
            event_counts.get(event, 0) + 1
        )
        product = find_product(item["product_id"])
        if product:
            category = product["category"]
            category_counts[category] = (
                category_counts.get(category, 0) + 1
            )
    preferred_category = None
    if category_counts:
        preferred_category = max(
            category_counts,
            key=category_counts.get
        )
    return {
        "user_id": user["user_id"],
        "total_interactions": len(history),
        "event_breakdown": event_counts,
        "category_activity": category_counts,
        "most_active_category": preferred_category,
        "recent_activities": history[:10]
    }


# ==========================================
# ORDER MANAGEMENT APIs
# ==========================================

@app.post("/api/orders")
def place_order(
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    user_id = user["user_id"]

    cart = get_customer_cart(user_id)

    if not cart:
        raise HTTPException(
            status_code=400,
            detail="Your shopping cart is empty"
        )

    order_items = []
    total_amount = 0.0

    for item in cart:
        product = find_product(item["product_id"])

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item['product_id']} not found"
            )

        try:
            price = float(product.get("price", 0))
            quantity = int(item["quantity"])
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Invalid product price or quantity"
            )

        if price <= 0 or quantity < 1:
            raise HTTPException(
                status_code=400,
                detail="Product price and quantity must be valid"
            )

        item_total = round(price * quantity, 2)
        order_items.append({
            "product_id": item["product_id"],
            "product_title": str(product.get("title", "Unknown Product")),
            "quantity": quantity,
            "unit_price": price,
            "item_total": item_total
        })
        total_amount += item_total

    total_amount = round(total_amount, 2)

    order_id = create_order(
        user_id,
        order_items,
        total_amount
    )

    # Record each purchased product for recommendation learning.
    global interactions, engine
    purchase_records = []

    for item in order_items:
        save_interaction(
            user_id,
            item["product_id"],
            "purchase"
        )
        purchase_records.append({
            "user_id": user_id,
            "product_id": item["product_id"],
            "event_type": "purchase",
            "rating": None
        })

    if purchase_records:
        interactions = pd.concat(
            [interactions, pd.DataFrame(purchase_records)],
            ignore_index=True
        )
        engine = RecommendationEngine(products, interactions)

    return {
        "message": "Order placed successfully",
        "order_id": order_id,
        "user_id": user_id,
        "total_items": sum(item["quantity"] for item in order_items),
        "total_amount": total_amount,
        "status": "pending",
        "items": order_items
    }


@app.get("/api/orders")
def customer_order_history(
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    orders = get_customer_orders(user["user_id"])

    return {
        "user_id": user["user_id"],
        "total_orders": len(orders),
        "orders": orders
    }


@app.get("/api/orders/{order_id}")
def customer_order_details(
    order_id: str,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)
    order = get_order_by_id(order_id, user["user_id"])

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return {
        "message": "Order details retrieved successfully",
        "order": order
    }


@app.patch("/api/orders/{order_id}/cancel")
def cancel_order(
    order_id: str,
    authorization: str | None = Header(default=None)
):
    user = current_customer(authorization)

    cancelled = cancel_customer_order(
        order_id,
        user["user_id"]
    )

    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail="Order cannot be cancelled. It may not exist or is no longer pending."
        )

    return {
        "message": "Order cancelled successfully",
        "order_id": order_id,
        "status": "cancelled"
    }

# ==========================================
# METRICS API
# ==========================================
@app.get("/api/metrics")
def metrics():
    return engine.metrics()
