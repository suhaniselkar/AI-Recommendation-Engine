from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRODUCTS_PATH = DATA_DIR / "products.csv"
INTERACTIONS_PATH = DATA_DIR / "interactions.csv"

PRODUCTS = [
("P001","Wireless Headphones","Electronics","Over ear bluetooth headphones with noise cancellation","audio bluetooth wireless music"),
("P002","Mechanical Keyboard","Electronics","RGB mechanical keyboard for programming and gaming","computer typing gaming"),
("P003","Smart Watch","Electronics","Fitness tracking smartwatch with heart rate monitor","wearable fitness health"),
("P004","Running Shoes","Fashion","Lightweight running shoes for daily workouts","sports running fitness"),
("P005","Yoga Mat","Sports","Non slip yoga mat for home workouts","yoga exercise fitness"),
("P006","Protein Shaker","Sports","Leak proof shaker bottle for gym supplements","gym fitness bottle"),
("P007","Python Programming","Books","Beginner friendly guide to Python programming","coding software technology"),
("P008","Machine Learning Basics","Books","Practical introduction to machine learning algorithms","AI data science coding"),
("P009","Deep Learning with PyTorch","Books","Neural networks and deep learning using PyTorch","AI machine learning coding"),
("P010","Coffee Maker","Home","Compact coffee maker for home brewing","kitchen coffee appliance"),
("P011","Ergonomic Chair","Home","Adjustable ergonomic office chair for desk work","office comfort furniture"),
("P012","Desk Lamp","Home","LED desk lamp with adjustable brightness","office study lighting"),
("P013","Bluetooth Speaker","Electronics","Portable wireless speaker with rich sound","audio bluetooth music"),
("P014","Casual Backpack","Fashion","Everyday backpack with laptop compartment","travel college bag"),
("P015","Water Bottle","Sports","Reusable insulated stainless steel water bottle","fitness hydration travel"),
("P016","Data Science Handbook","Books","Hands on data analysis with Python and pandas","data science python analytics"),
("P017","Gaming Mouse","Electronics","Precision wireless mouse for gaming and work","computer gaming accessories"),
("P018","Air Fryer","Home","Digital air fryer for quick home cooking","kitchen appliance cooking"),
("P019","Cycling Helmet","Sports","Ventilated protective helmet for cycling","cycling outdoor safety"),
("P020","Web Development Guide","Books","Learn HTML CSS JavaScript and modern web development","coding web frontend"),
]
def ensure_demo_data():
    DATA_DIR.mkdir(exist_ok=True)
    if not PRODUCTS_PATH.exists():
        pd.DataFrame(PRODUCTS, columns=["product_id","title","category","description","tags"]).to_csv(PRODUCTS_PATH,index=False)
    if not INTERACTIONS_PATH.exists():
        rng=np.random.default_rng(42)
        rows=[]
        # Synthetic preference clusters create meaningful demo recommendations.
        interests = {
          "U001":["Electronics","Books"], "U002":["Sports","Fashion"],
          "U003":["Books","Electronics"], "U004":["Home","Books"],
          "U005":["Sports","Electronics"], "U006":["Fashion","Home"],
          "U007":["Books","Home"], "U008":["Electronics","Sports"],
          "U009":["Home","Fashion"], "U010":["Books","Sports"],
          "U011":["Electronics","Home"], "U012":["Fashion","Sports"]
        }
        products=pd.DataFrame(PRODUCTS,columns=["product_id","title","category","description","tags"])
        for user,cats in interests.items():
            candidates=products[products.category.isin(cats)].product_id.tolist()
            for pid in rng.choice(candidates,size=min(7,len(candidates)),replace=False):
                rows.append((user,pid,"purchase" if rng.random()<.25 else "view",int(rng.integers(3,6))))
            # A few cross-category views make the data less artificial.
            for pid in rng.choice(products[~products.product_id.isin(candidates)].product_id,size=2,replace=False):
                rows.append((user,pid,"view",int(rng.integers(2,5))))
        pd.DataFrame(rows,columns=["user_id","product_id","event_type","rating"]).to_csv(INTERACTIONS_PATH,index=False)
    return PRODUCTS_PATH, INTERACTIONS_PATH
