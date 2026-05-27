import os
import glob
import json
import streamlit as st


def _human_readable_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:3.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _get_item_size(path: str) -> int:
    if os.path.isfile(path):
        return os.path.getsize(path)
    if os.path.isdir(path):
        total = 0
        for dirpath, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                fp = os.path.join(dirpath, filename)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
        return total
    return 0


def _is_valid_name(name: str) -> bool:
    return not name.startswith(".") and name != "__pycache__"


def _scan_products():
    products = []
    base_dir = os.path.dirname(__file__)

    catalog = [
        ("../../products/apps/", "📱", False),
        ("../../products/assets/", "📖", True),
        ("../../content/blog/", "📝", False),
        ("../../content/affiliate/", "🔗", False),
    ]

    for rel_dir, icon, skip_zips in catalog:
        abs_dir = os.path.normpath(os.path.join(base_dir, rel_dir))
        if not os.path.isdir(abs_dir):
            continue
        for item_path in glob.glob(os.path.join(abs_dir, "*")):
            name = os.path.basename(item_path)
            if not _is_valid_name(name):
                continue
            if skip_zips and name.lower().endswith(".zip"):
                continue
            products.append(
                {
                    "name": name,
                    "path": item_path,
                    "icon": icon,
                    "size": _get_item_size(item_path),
                }
            )
    return products


def render_marketplace():
    st.title("Monetization Marketplace")
    st.caption("Browse and manage all monetizable products and content.")

    products = _scan_products()

    # Ensure session state defaults
    for i, prod in enumerate(products):
        uid = f"prod_{i}"
        prod["uid"] = uid
        st.session_state.setdefault(f"status_{uid}", "Draft")
        st.session_state.setdefault(f"price_{uid}", 0.0)
        st.session_state.setdefault(f"platform_{uid}", "Not listed")

    # Summary metrics
    total = len(products)
    listed = sum(
        1 for p in products if st.session_state.get(f"status_{p['uid']}", "Draft") == "Listed"
    )
    published = sum(
        1 for p in products if st.session_state.get(f"status_{p['uid']}", "Draft") == "Published"
    )
    total_value = sum(
        st.session_state.get(f"price_{p['uid']}", 0.0)
        for p in products
        if st.session_state.get(f"status_{p['uid']}", "Draft") in ("Listed", "Published", "Sold")
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Products", total)
    m2.metric("Listed", listed)
    m3.metric("Published", published)
    m4.metric("Total Value", f"${total_value:,.2f}")

    st.divider()

    # Bulk actions
    with st.expander("Bulk Actions"):
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Export product manifest as JSON"):
                manifest = []
                for p in products:
                    manifest.append(
                        {
                            "name": p["name"],
                            "path": p["path"],
                            "icon": p["icon"],
                            "size": _human_readable_size(p["size"]),
                            "status": st.session_state.get(f"status_{p['uid']}", "Draft"),
                            "price": st.session_state.get(f"price_{p['uid']}", 0.0),
                            "platform": st.session_state.get(f"platform_{p['uid']}", "Not listed"),
                        }
                    )
                json_bytes = json.dumps(manifest, indent=2).encode("utf-8")
                st.download_button(
                    label="Download JSON",
                    data=json_bytes,
                    file_name="product_manifest.json",
                    mime="application/json",
                )
        with b2:
            bulk_price = st.number_input(
                "Set all prices ($)",
                min_value=0.0,
                value=0.0,
                step=1.0,
                key="bulk_price_input",
            )
            if st.button("Set all prices at once"):
                for p in products:
                    st.session_state[f"price_{p['uid']}"] = bulk_price
                st.success("All prices updated!")
                st.rerun()

    st.divider()

    if not products:
        st.info("No products found. Generate some products to populate the marketplace.")
        return

    # Grid layout
    columns = st.columns(3)
    for idx, prod in enumerate(products):
        col = columns[idx % 3]
        with col:
            with st.container(border=True):
                st.markdown(f"**{prod['icon']} {prod['name']}**")
                st.caption(f"`{prod['path']}`")
                st.text(f"Size: {_human_readable_size(prod['size'])}")

                st.selectbox(
                    "Status",
                    ["Draft", "Listed", "Published", "Sold"],
                    key=f"status_{prod['uid']}",
                )
                st.number_input(
                    "Price ($)",
                    min_value=0.0,
                    value=0.0,
                    step=0.99,
                    key=f"price_{prod['uid']}",
                )
                st.selectbox(
                    "Platform",
                    ["Gumroad", "Etsy", "Amazon", "Shopify", "Self-hosted", "Not listed"],
                    key=f"platform_{prod['uid']}",
                )
                if st.button("Copy path", key=f"copy_{prod['uid']}"):
                    st.code(prod["path"], language=None)
