# Stripe API Quick Reference

## Authentication
- Get API keys from https://dashboard.stripe.com/apikeys
- Secret key format: `sk_test_...` or `sk_live_...`
- Header: `Authorization: Bearer <sk_...>`
- Base URL: `https://api.stripe.com/v1/`

## Key Endpoints

### Create Product
POST /products
Body (form-encoded):
- name: Product Name
- description: Product description
- images[]: https://image-url.jpg

### Create Price
POST /prices
Body:
- product: prod_xxx
- unit_amount: 2000 (cents, so $20.00)
- currency: usd

### Create Checkout Session
POST /checkout/sessions
Body:
- mode: payment
- line_items[0][price]: price_xxx
- line_items[0][quantity]: 1
- success_url: https://yourdomain.com/success
- cancel_url: https://yourdomain.com/cancel

### Python SDK Example
```python
import stripe
stripe.api_key = "sk_test_..."

session = stripe.checkout.Session.create(
    mode="payment",
    line_items=[{"price": "price_xxx", "quantity": 1}],
    success_url="https://yourdomain.com/success",
    cancel_url="https://yourdomain.com/cancel",
)
print(session.url)  # Send customer here
```
