# Printify API Quick Reference

## Authentication
- Get API key from https://printify.com/app/account/api
- Header: `Authorization: Bearer <your_api_key>`
- Base URL: `https://api.printify.com/v1/`

## Key Endpoints

### List Shops
GET /shops.json
Response: [{"id": 123, "title": "My Store"}]

### List Products
GET /shops/{shop_id}/products.json

### Create Product
POST /shops/{shop_id}/products.json
Body:
{
  "title": "Product Title",
  "description": "Product description...",
  "blueprint_id": 5,
  "print_provider_id": 1,
  "variants": [
    {"id": 123, "price": 1500, "is_enabled": true}
  ],
  "print_areas": [
    {
      "variant_ids": [123],
      "placeholders": [
        {
          "position": "front",
          "images": [
            {"id": "image_id", "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0}
          ]
        }
      ]
    }
  ]
}

### Publish Product
POST /shops/{shop_id}/products/{product_id}/publish.json

### List Blueprints
GET /catalog/blueprints.json
Popular: T-shirts (6), Hoodies (77), Mugs (39), Posters (40), Phone cases (84)

### List Print Providers
GET /catalog/blueprints/{blueprint_id}/print_providers.json
