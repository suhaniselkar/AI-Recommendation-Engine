
const $=id=>document.getElementById(id);

const IMAGE={
P001:"https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=900&auto=format&fit=crop&q=85",
P002:"https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=900&auto=format&fit=crop&q=85",
P003:"https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=900&auto=format&fit=crop&q=85",
P004:"https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=900&auto=format&fit=crop&q=85",
P005:"https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=900&auto=format&fit=crop&q=85",
P006:"https://images.unsplash.com/photo-1579758629938-03607ccdbaba?w=900&auto=format&fit=crop&q=85",
P007:"https://images.unsplash.com/photo-1532012197267-da84d127e765?w=900&auto=format&fit=crop&q=85",
P008:"https://images.unsplash.com/photo-1512820790803-83ca734da794?w=900&auto=format&fit=crop&q=85",
P009:"https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=900&auto=format&fit=crop&q=85",
P010:"https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=900&auto=format&fit=crop&q=85",
P011:"/static/images/ergonomic-chair.svg",
P012:"https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=900&auto=format&fit=crop&q=85",
P013:"https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=900&auto=format&fit=crop&q=85",
P014:"https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=900&auto=format&fit=crop&q=85",
P015:"https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=900&auto=format&fit=crop&q=85",
P016:"https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=900&auto=format&fit=crop&q=85",
P017:"https://images.unsplash.com/photo-1527814050087-3793815479db?w=900&auto=format&fit=crop&q=85",
P018:"/static/images/air-fryer.svg",
P019:"https://images.unsplash.com/photo-1507035895480-2b3156c31fc8?w=900&auto=format&fit=crop&q=85",
P020:"https://images.unsplash.com/photo-1491897554428-130a60dd4757?w=900&auto=format&fit=crop&q=85"
};

let products=[];
let recommendations=[];
let cartItems=[];
let wishlistItems=[];
let activeCategory="All";
let activeUser="";
let authMode="login";
let customer=null;
let authToken=localStorage.getItem("reco-token")||"";

const money=n=>"₹"+Number(n).toLocaleString("en-IN");

const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({
"&":"&amp;",
"<":"&lt;",
">":"&gt;",
'"':"&quot;",
"'":"&#39;"
}[c]));

function photo(id,title){
 return `<div class="product-photo"><img src="${IMAGE[id]||""}" alt="${esc(title)}" loading="lazy" onerror="this.onerror=null;this.parentElement.classList.add('photo-fallback');this.remove()"></div>`;
}

function price(p){
 const value=Number(p.price ?? p.unit_price ?? p.display_price);
 return Number.isFinite(value)&&value>0
  ?value
  :499+(parseInt(String(p.product_id).slice(1),10)||1)*137;
}

function productCard(p,isRec=false){
 let saved=getWishlistIds().includes(String(p.product_id));
 let pr=price(p);

 return `<article class="product-card">
  ${photo(p.product_id,p.title)}
  <span class="product-badge">${esc(p.category)}</span>
  <button class="wish-btn ${saved?"saved":""}" data-wish="${p.product_id}" title="Save to wishlist">${saved?"♥":"♡"}</button>
  <div class="product-info">
   <div class="product-title-row">
    <h3>${esc(p.title)}</h3>
    <span class="category-label">${esc(p.category)}</span>
   </div>
   <p class="product-desc">${esc(p.description)}</p>
   <div class="product-bottom">
    <span class="product-price">${money(pr)}</span>
    ${isRec?`<span class="match">✦ ${(p.score*100).toFixed(0)}% match</span>`:""}
   </div>
   <div class="card-actions">
    <button class="add-btn" data-add="${p.product_id}">Add to bag</button>
    <button class="quick-btn" data-wish="${p.product_id}">${saved?"Saved ♥":"♡ Save"}</button>
   </div>
  </div>
 </article>`;
}

async function api(url,options={}){
 const headers={...(options.headers||{})};

 if(authToken){
  headers.Authorization=`Bearer ${authToken}`;
 }

 if(options.body&&!headers["Content-Type"]){
  headers["Content-Type"]="application/json";
 }

 const response=await fetch(url,{...options,headers});
 const raw=await response.text();

 let data={};

 try{
  data=raw?JSON.parse(raw):{};
 }catch{
  data={detail:raw||"Unexpected server response"};
 }

 if(!response.ok){
  const detail=data.detail;

  const message=Array.isArray(detail)
   ?detail.map(x=>x.msg||JSON.stringify(x)).join("; ")
   :(typeof detail==="string"?detail:`Request failed (${response.status})`);

  throw new Error(message);
 }

 return data;
}

async function get(url){
 const response=await fetch(url);
 const raw=await response.text();

 let data={};

 try{
  data=raw?JSON.parse(raw):{};
 }catch{
  data={detail:raw};
 }

 if(!response.ok){
  throw new Error(data.detail||`Request failed (${response.status})`);
 }

 return data;
}

function getProduct(id){
 return products.find(p=>String(p.product_id)===String(id));
}

function productPrice(product){
 if(!product)return 0;

 const value=Number(
  product.price??product.unit_price??product.display_price
 );

 return Number.isFinite(value)?value:0;
}

function getWishlistIds(){
 return wishlistItems.map(item=>String(item.product_id));
}

function getCartRows(){
 return cartItems.map(item=>({
  product_id:String(item.product_id),
  quantity:Number(item.quantity)||1,
  price:Number(item.unit_price??item.product?.price??0),
  product:item.product||getProduct(item.product_id)
 }));
}

async function init(){

 const [us,cs,ps]=await Promise.all([
  get("/api/users"),
  get("/api/categories"),
  get("/api/products")
 ]);

 products=Array.isArray(ps)
  ?ps
  :(Array.isArray(ps?.products)?ps.products:[]);

 const users=Array.isArray(us)
  ?us
  :(Array.isArray(us?.users)?us.users:[]);

 const categories=Array.isArray(cs)
  ?cs
  :(Array.isArray(cs?.categories)?cs.categories:[]);

 if(!products.length){
  throw Error("The products API returned no product list. Check GET /api/products.");
 }

 const firstUser=users[0];

 activeUser=firstUser
  ?(typeof firstUser==="string"?firstUser:firstUser.user_id)
  :"U001";

 $("user").innerHTML=users.map(u=>
  `<option value="${esc(typeof u==="string"?u:u.user_id)}">${esc(typeof u==="string"?u:(u.name||u.user_id))}</option>`
 ).join("");

 $("profile-user").innerHTML=$("user").innerHTML;

 if(activeUser){
  $("user").value=activeUser;
 }

 $("profile-user").value=$("user").value;

 $("category").innerHTML=
  '<option value="All">All categories</option>'+
  categories.map(c=>`<option>${esc(typeof c==="string"?c:c.name)}</option>`).join("");

 $("category-pills").innerHTML=["All",...categories.map(c=>
  typeof c==="string"?c:c.name
 )].map(c=>
  `<button class="category-pill ${c==="All"?"active":""}" data-cat="${esc(c)}">${esc(c)}</button>`
 ).join("");

 $("products").innerHTML=products.map(p=>productCard(p)).join("");

 renderCounts();
 renderCart();
 renderWishlist();

 if(authToken){
  try{
   const data=await api("/api/auth/me");

   setCustomer(data.customer);

   await loadCustomerData();

  }catch(error){
   authToken="";
   customer=null;

   localStorage.removeItem("reco-token");

   console.warn("Saved session is no longer valid:",error.message);

   updateAccountButton();
  }
 }

 await loadRecommendations();
}

async function loadRecommendations(){

 $("recommendations-list").innerHTML=
  '<div class="loading">Finding your picks…</div>';

 activeUser=$("user").value||"U001";

 const method=$("method").value;

 try{

  const data=await get(
   `/api/recommendations/${encodeURIComponent(activeUser)}?limit=4&method=${encodeURIComponent(method)}`
  );

  recommendations=Array.isArray(data)
   ?data
   :(Array.isArray(data?.recommendations)?data.recommendations:[]);

  $("recommendations-list").innerHTML=
   recommendations.map(p=>productCard(p,true)).join("")||
   '<p class="loading">No personalized picks yet. Explore products or sign in to build your recommendations.</p>';

 }catch(error){

  recommendations=[];

  $("recommendations-list").innerHTML=
   `<p class="loading">Recommendations are temporarily unavailable: ${esc(error.message)}</p>`;
 }
}

function filteredProducts(){

 let q=$("search").value.trim().toLowerCase();
 let cat=$("category").value;
 let sort=$("sort").value;

 let list=products.filter(p=>
  (cat==="All"||p.category===cat)&&
  (activeCategory==="All"||p.category===activeCategory)&&
  (!q||`${p.title} ${p.category} ${p.description}`.toLowerCase().includes(q))
 );

 if(sort==="az"){
  list.sort((a,b)=>a.title.localeCompare(b.title));
 }

 return list;
}

function renderCatalog(){

 let list=filteredProducts();

 $("products").innerHTML=
  list.map(p=>productCard(p)).join("")||
  '<p class="loading">No products found. Try another search.</p>';
}

function updateAccountButton(){

 if(customer){

  const name=customer.name||"Account";

  $("profile-open").innerHTML=
   `<span class="avatar">${esc(name.charAt(0).toUpperCase())}</span><span class="profile-label">${esc(name.split(" ")[0])}</span><span>⌄</span>`;

 }else{

  $("profile-open").innerHTML=
   '<span class="avatar">U</span><span class="profile-label">Sign in</span><span>⌄</span>';
 }
}

function setCustomer(c){

 customer=c||null;

 if(customer){

  let option=[...$("user").options].find(
   o=>o.value===customer.user_id
  );

  if(!option){

   option=document.createElement("option");
   option.value=customer.user_id;
   option.textContent=(customer.name||"Customer")+" (account)";

   $("user").appendChild(option);
  }

  $("user").value=customer.user_id;
  $("profile-user").value=customer.user_id;
 }

 updateAccountButton();
 renderCounts();
}

async function loadCustomerData(){

 if(!customer)return;

 const [wishlistData,cartData]=await Promise.all([
  api("/api/wishlist"),
  api("/api/cart")
 ]);

 wishlistItems=Array.isArray(wishlistData.wishlist)
  ?wishlistData.wishlist
  :[];

 cartItems=Array.isArray(cartData.cart)
  ?cartData.cart
  :[];

 renderCatalog();

 $("recommendations-list").innerHTML=
  recommendations.map(p=>productCard(p,true)).join("");

 renderWishlist();
 renderCart();
 renderCounts();
}

function openAuth(mode="login"){

 authMode=mode;

 $("auth-error").textContent="";
 $("auth-form").reset();

 $("name-field").classList.toggle("hidden",mode!=="register");

 $("auth-title").textContent=
  mode==="login"?"Welcome back.":"Create your account.";

 $("auth-subtitle").textContent=
  mode==="login"
   ?"Sign in to save your picks and personalize your experience."
   :"Join Reco to keep your favourites and shopping activity together.";

 $("auth-submit").innerHTML=
  mode==="login"
   ?'Sign in <span>→</span>'
   :'Create account <span>→</span>';

 $("login-tab").classList.toggle("active",mode==="login");
 $("register-tab").classList.toggle("active",mode==="register");

 $("overlay").classList.add("open");
 $("auth-modal").classList.add("open");
}

async function submitAuth(e){

 e.preventDefault();

 $("auth-error").textContent="";

 const body={
  email:$("auth-email").value.trim(),
  password:$("auth-password").value
 };

 if(authMode==="register"){
  body.name=$("auth-name").value.trim();
 }

 $("auth-submit").disabled=true;
 $("auth-submit").textContent="Please wait…";

 try{

  const data=await api(
   authMode==="login"?"/api/auth/login":"/api/auth/register",
   {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(body)
   }
  );

  authToken=data.token;

  localStorage.setItem("reco-token",authToken);

  setCustomer(data.customer);

  closeAll();

  await loadCustomerData();
  await loadRecommendations();

  toast(
   authMode==="login"
    ?"You are signed in!"
    :"Your account is ready!"
  );

 }catch(error){

  $("auth-error").textContent=error.message;

 }finally{

  $("auth-submit").disabled=false;

  $("auth-submit").innerHTML=
   authMode==="login"
    ?'Sign in <span>→</span>'
    :'Create account <span>→</span>';
 }
}

async function signOut(){

 try{
  if(authToken){
   await api("/api/auth/logout",{method:"POST"});
  }
 }catch(error){
  console.warn(error);
 }

 authToken="";
 customer=null;
 cartItems=[];
 wishlistItems=[];

 localStorage.removeItem("reco-token");

 closeAll();

 setCustomer(null);

 renderCatalog();
 renderWishlist();
 renderCart();

 await loadRecommendations();

 toast("You have signed out");
}

async function loadCart(){

 if(!customer){
  cartItems=[];
  renderCart();
  renderCounts();
  return;
 }

 const data=await api("/api/cart");

 cartItems=Array.isArray(data.cart)
  ?data.cart
  :[];

 renderCart();
 renderCounts();
}

async function loadWishlist(){

 if(!customer){
  wishlistItems=[];
  renderWishlist();
  renderCounts();
  return;
 }

 const data=await api("/api/wishlist");

 wishlistItems=Array.isArray(data.wishlist)
  ?data.wishlist
  :[];

 renderCatalog();

 $("recommendations-list").innerHTML=
  recommendations.map(p=>productCard(p,true)).join("");

 renderWishlist();
 renderCounts();
}

async function addToCart(id){

 if(!customer){
  openAuth("login");
  return;
 }

 try{

  await api("/api/cart",{
   method:"POST",
   body:JSON.stringify({
    product_id:id,
    quantity:1
   })
  });

  await loadCart();

  toast("Added to your bag");

 }catch(error){

  toast(error.message);
 }
}

async function toggleWish(id){

 if(!customer){
  openAuth("login");
  return;
 }

 const exists=getWishlistIds().includes(String(id));

 try{

  if(exists){

   await api(
    `/api/wishlist/${encodeURIComponent(id)}`,
    {method:"DELETE"}
   );

  }else{

   await api("/api/wishlist",{
    method:"POST",
    body:JSON.stringify({product_id:id})
   });
  }

  await loadWishlist();

  toast(
   exists
    ?"Removed from wishlist"
    :"Saved to wishlist"
  );

 }catch(error){

  toast(error.message);
 }
}

async function updateCartQuantity(id,quantity){

 if(!customer)return;

 try{

  if(quantity<=0){

   await api(
    `/api/cart/${encodeURIComponent(id)}`,
    {method:"DELETE"}
   );

  }else{

   await api(
    `/api/cart/${encodeURIComponent(id)}`,
    {
     method:"PATCH",
     body:JSON.stringify({quantity})
    }
   );
  }

  await loadCart();

 }catch(error){

  toast(error.message);
 }
}


function openCheckout(){
 if(!customer){openAuth("login");return;}
 const rows=getCartRows();
 if(!rows.length){toast("Your cart is empty");return;}
 const total=rows.reduce((sum,row)=>sum+(Number(row.price||productPrice(row.product))*row.quantity),0);
 $("checkout-content").innerHTML=`
  <div class="checkout-summary">
   ${rows.map(row=>`<div class="checkout-row"><span>${esc(row.product?.title||row.product_id)} × ${row.quantity}</span><b>${money((Number(row.price||productPrice(row.product)))*row.quantity)}</b></div>`).join("")}
   <div class="checkout-total"><span>Order total</span><b>${money(total)}</b></div>
  </div>
  <div class="checkout-payment"><b>Payment method</b><p>Cash on Delivery (Demo)</p><small>No online payment will be collected.</small></div>
  <button class="primary-btn full" id="place-order-btn" type="button">Place order <span>→</span></button>
  <p class="demo-note">By placing this demo order, you confirm the items and total shown above.</p>`;
 $("overlay").classList.add("open");
 $("checkout-modal").classList.add("open");
 $("place-order-btn").onclick=placeOrder;
}

async function placeOrder(){
 const button=$("place-order-btn");
 button.disabled=true;
 button.textContent="Placing order…";
 try{
  const data=await api("/api/orders",{method:"POST"});
  $("checkout-modal").classList.remove("open");
  closeAll();
  await loadCart();
  $("order-success-content").innerHTML=`
   <div class="order-success-mark">✓</div>
   <p class="eyebrow">ORDER CONFIRMED</p>
   <h2>Thank you for your order!</h2>
   <p class="section-sub">Your order has been placed successfully.</p>
   <div class="order-id-box"><span>Order ID</span><b>${esc(data.order_id)}</b></div>
   <div class="checkout-total"><span>Total paid</span><b>${money(data.total_amount)}</b></div>
   <p class="demo-note">Payment method: Cash on Delivery (Demo). No payment was collected.</p>
   <button class="primary-btn full" id="success-orders-btn">View my orders</button>
   <button class="quick-btn full" id="success-done-btn" style="margin-top:9px">Continue shopping</button>`;
  $("overlay").classList.add("open");
  $("order-success-modal").classList.add("open");
  $("success-orders-btn").onclick=()=>{closeAll();openOrders();};
  $("success-done-btn").onclick=closeAll;
  toast("Order placed successfully");
 }catch(error){
  toast(error.message);
  button.disabled=false;
  button.innerHTML='Place order <span>→</span>';
 }
}

async function openOrders(){
 if(!customer){openAuth("login");return;}
 $("orders-content").innerHTML='<p class="loading">Loading your orders…</p>';
 $("overlay").classList.add("open");
 $("orders-modal").classList.add("open");
 try{
  const data=await api("/api/orders");
  const orders=Array.isArray(data.orders)?data.orders:[];
  $("orders-content").innerHTML=orders.length?orders.map(order=>`
   <div class="order-card">
    <div class="order-card-top"><b>${esc(order.order_id)}</b><span class="order-status ${String(order.status).toLowerCase()}">${esc(order.status)}</span></div>
    <div class="order-card-meta"><span>${esc(order.created_at||order.order_date||"Order placed")}</span><b>${money(order.total_amount||0)}</b></div>
    <div class="order-card-actions">
     <button class="quick-btn" data-order-view="${esc(order.order_id)}">View details</button>
     ${String(order.status).toLowerCase()==="pending"?`<button class="quick-btn cancel-order-btn" data-order-cancel="${esc(order.order_id)}">Cancel order</button>`:""}
    </div>
   </div>`).join(""):'<div class="empty-state"><strong>No orders yet.</strong>Your placed orders will appear here.</div>';
 }catch(error){$("orders-content").innerHTML=`<p class="auth-error">${esc(error.message)}</p>`;}
}

async function showOrderDetails(id){
 $("orders-content").innerHTML='<p class="loading">Loading order details…</p>';
 try{
  const data=await api(`/api/orders/${encodeURIComponent(id)}`);
  const order=data.order||{};
  const items=Array.isArray(order.items)?order.items:[];
  $("orders-content").innerHTML=`
   <button class="quick-btn" id="back-orders">← Back to orders</button>
   <div class="order-card">
    <div class="order-card-top"><b>${esc(order.order_id||id)}</b><span class="order-status ${String(order.status).toLowerCase()}">${esc(order.status||"")}</span></div>
    ${items.map(item=>`<div class="checkout-row"><span>${esc(item.product_title||item.title||item.product_id)} × ${Number(item.quantity)||1}</span><b>${money(item.item_total||0)}</b></div>`).join("")}
    <div class="checkout-total"><span>Order total</span><b>${money(order.total_amount||0)}</b></div>
   </div>`;
  $("back-orders").onclick=openOrders;
 }catch(error){toast(error.message);openOrders();}
}

async function cancelOrder(id){
 if(!window.confirm("Are you sure you want to cancel this order?"))return;
 try{
  await api(`/api/orders/${encodeURIComponent(id)}/cancel`,{method:"PATCH"});
  toast("Order cancelled");
  await openOrders();
 }catch(error){toast(error.message);}
}

function renderCounts(){

 const cartCount=getCartRows().reduce(
  (sum,row)=>sum+row.quantity,
  0
 );

 const wishCount=getWishlistIds().length;

 $("cart-count").textContent=cartCount;
 $("wish-count").textContent=wishCount;

 $("profile-cart").textContent=cartCount;
 $("profile-wish").textContent=wishCount;
}

function toast(msg){

 const element=$("toast");

 element.textContent=msg;
 element.classList.add("show");

 clearTimeout(window.toastTimer);

 window.toastTimer=setTimeout(
  ()=>element.classList.remove("show"),
  2200
 );
}

function renderCart(){

 const rows=getCartRows();

 const count=rows.reduce(
  (sum,row)=>sum+row.quantity,
  0
 );

 let total=0;

 $("drawer-count").textContent=`(${count})`;

 $("cart-items").innerHTML=rows.length
  ?rows.map(row=>{

   const p=row.product||getProduct(row.product_id);

   if(!p)return"";

   const unitPrice=Number(
    row.price||productPrice(p)
   );

   const lineTotal=unitPrice*row.quantity;

   total+=lineTotal;

   return `<div class="cart-line">
      ${photo(row.product_id,p.title).replace('product-photo','cart-photo')}
      <div>
        <h4>${esc(p.title)}</h4>
        <small>${money(unitPrice)}</small>
        <div class="qty">
          <button data-qty="${row.product_id}" data-delta="-1">−</button>
          <span>${row.quantity}</span>
          <button data-qty="${row.product_id}" data-delta="1">+</button>
        </div>
      </div>
      <div>
        <b class="line-price">${money(lineTotal)}</b>
        <button class="remove-line" data-remove="${row.product_id}">×</button>
      </div>
    </div>`;

  }).join("")
  :'<div class="empty-state"><strong>Your bag is taking a break.</strong>Add a few lovely finds to get started.</div>';

 $("subtotal").textContent=money(total);

 renderCounts();
}

function renderWishlist(){

 const list=wishlistItems.map(item=>
  item.product||getProduct(item.product_id)
 ).filter(Boolean);

 $("wishlist-items").innerHTML=list.length
  ?list.map(p=>`
    <div class="cart-line wishlist-line">
      ${photo(p.product_id,p.title).replace('product-photo','cart-photo')}
      <div class="wishlist-details">
        <h4>${esc(p.title)}</h4>
        <small>${money(productPrice(p))}</small>
        <div class="wishlist-actions">
          <button class="add-btn wishlist-add-btn" type="button" data-add="${p.product_id}">Add to bag</button>
        </div>
      </div>
      <button class="remove-line wishlist-remove-btn" type="button" data-wish="${p.product_id}" aria-label="Remove ${esc(p.title)} from wishlist">♥</button>
    </div>
  `).join("")
  :'<div class="empty-state"><strong>No saved finds yet.</strong>Tap the heart on any product to keep it here.</div>';

 renderCounts();
}

function openDrawer(id){

 $("overlay").classList.add("open");
 $(id).classList.add("open");
}

function closeAll(){

 $("overlay").classList.remove("open");

 document.querySelectorAll(".drawer").forEach(x=>
  x.classList.remove("open")
 );

 $("profile-modal").classList.remove("open");
 $("auth-modal").classList.remove("open");
 ["checkout-modal","orders-modal","order-success-modal"].forEach(id=>{
  const element=$(id);
  if(element)element.classList.remove("open");
 });
}

document.addEventListener("click",e=>{

 const add=e.target.closest("[data-add]");

 if(add){
  addToCart(add.dataset.add);
 }

 const wish=e.target.closest("[data-wish]");

 if(wish){
  toggleWish(wish.dataset.wish);
 }

 const qty=e.target.closest("[data-qty]");

 if(qty){

  const row=getCartRows().find(
   item=>item.product_id===qty.dataset.qty
  );

  if(row){
   updateCartQuantity(
    row.product_id,
    row.quantity+Number(qty.dataset.delta)
   );
  }
 }

 const remove=e.target.closest("[data-remove]");

 if(remove){
  updateCartQuantity(remove.dataset.remove,0);
 }

 const cat=e.target.closest("[data-cat]");

 if(cat){

  activeCategory=cat.dataset.cat;

  $("category").value=activeCategory;

  document.querySelectorAll(".category-pill").forEach(b=>
   b.classList.toggle(
    "active",
    b.dataset.cat===activeCategory
   )
  );

  renderCatalog();
 }

 if(e.target.closest("[data-close]")){
  closeAll();
 }
});

$("cart-open").onclick=async()=>{

 if(customer){
  try{
   await loadCart();
  }catch(error){
   toast(error.message);
  }
 }

 renderCart();

 openDrawer("cart-drawer");
};

$("wishlist-open").onclick=async()=>{

 if(customer){
  try{
   await loadWishlist();
  }catch(error){
   toast(error.message);
  }
 }

 renderWishlist();

 openDrawer("wishlist-drawer");
};

$("profile-open").onclick=()=>{

 if(!customer){
  openAuth("login");
  return;
 }

 $("profile-user").value=$("user").value;

 renderCounts();

 $("overlay").classList.add("open");
 $("profile-modal").classList.add("open");
};

$("login-tab").onclick=()=>openAuth("login");
$("register-tab").onclick=()=>openAuth("register");

$("auth-form").onsubmit=submitAuth;

$("auth-modal").querySelector("[data-close]").onclick=closeAll;
$("overlay").onclick=closeAll;

$("save-profile").onclick=async()=>{

 $("user").value=$("profile-user").value;

 closeAll();

 await loadRecommendations();

 toast("Profile updated");
};

$("signout").onclick=signOut;

$("user").onchange=loadRecommendations;
$("method").onchange=loadRecommendations;

$("category").onchange=()=>{

 activeCategory=$("category").value;

 document.querySelectorAll(".category-pill").forEach(b=>
  b.classList.toggle(
   "active",
   b.dataset.cat===activeCategory
  )
 );

 renderCatalog();
};

$("sort").onchange=renderCatalog;
$("search").oninput=renderCatalog;

$("checkout").onclick=openCheckout;
$("my-orders").onclick=()=>{closeAll();openOrders();};
$("checkout-modal").querySelector("[data-close]").onclick=closeAll;
$("orders-modal").querySelector("[data-close]").onclick=closeAll;
$("order-success-modal").querySelector("[data-close]").onclick=closeAll;

$("orders-content").addEventListener("click",e=>{
 const view=e.target.closest("[data-order-view]");
 if(view)showOrderDetails(view.dataset.orderView);
 const cancel=e.target.closest("[data-order-cancel]");
 if(cancel)cancelOrder(cancel.dataset.orderCancel);
});

$("newsletter-form").onsubmit=e=>{

 e.preventDefault();

 toast("Thanks for joining the demo list!");

 e.target.reset();
};

init().catch(e=>{

 $("products").innerHTML=
  `<p class="loading">Could not load catalog: ${esc(e.message)}</p>`;

 $("recommendations-list").innerHTML=
  `<p class="loading">Recommendations are unavailable until the catalog loads.</p>`;
});
