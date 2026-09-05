import os
import sqlite3
import pandas as pd
import streamlit as st

DB_FILE = "gfd_inventory.db"
CANONICAL_WORKS_FILE = "rep_list.txt"


# Load rep list
@st.cache_data
def load_canonical_works(filepath=CANONICAL_WORKS_FILE):
    """Loads and caches canonical works from a text file for autocomplete."""
    if not os.path.exists(filepath):
        # Fallback default canonical titles if text file isn't created yet
        return [
            "From Before",
            "Oatka Trail",
            "Prelude",
            "Never Top 40 (Jukebox)",
            "Griot New York",
            "Moth Dreams",
            "The Lion King",
            "DanceCollageForRomie",
        ]

    with open(filepath, "r", encoding="utf-8") as f:
        works = [line.strip() for line in f if line.strip()]
    return sorted(works)


# Page Configuration
st.set_page_config(
    page_title="Garth Fagan Dance — AV Collection Catalog",
    page_icon="🎭",
    layout="wide",
)


# -----------------------------------------------------------------------------
# DATABASE SETUP & HELPERS
# -----------------------------------------------------------------------------


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            media_id TEXT PRIMARY KEY,
            physical_format TEXT NOT NULL,
            brand_stock TEXT,
            tape_length TEXT,
            media_case_label TEXT,
            item_title TEXT NOT NULL,
            date_on_label TEXT,
            production_reel_info TEXT,
            generation_level TEXT,
            collection_series TEXT,
            box_number TEXT,
            physical_condition TEXT,
            baking_flag TEXT,
            audio_track_info TEXT,
            estimated_runtime_min DECIMAL(10, 2),
            digitization_priority TEXT,
            is_unique TEXT,
            rights_status TEXT,
            digital_file_exists TEXT,
            digitization_status TEXT DEFAULT 'Not digitized',
            current_housing TEXT,
            misc_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Junction table enabling Many-to-Many relationship between Media and Works
    c.execute("""
        CREATE TABLE IF NOT EXISTS media_works (
            media_id TEXT NOT NULL,
            work_name TEXT NOT NULL,
            PRIMARY KEY (media_id, work_name),
            FOREIGN KEY (media_id) REFERENCES inventory (media_id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()


def fetch_inventory():
    """Retrieves all inventory items with aggregated canonical works."""
    conn = get_db_connection()
    query = """
        SELECT 
            i.media_id,
            i.item_title,
            i.physical_format,
            COALESCE(GROUP_CONCAT(w.work_name, ' | '), '[None Linked]') AS canonical_works,
            i.generation_level,
            i.collection_series,
            i.box_number,
            i.brand_stock,
            i.tape_length,
            i.media_case_label,
            i.date_on_label,
            i.production_reel_info,
            i.physical_condition,
            i.baking_flag,
            i.audio_track_info,
            i.estimated_runtime_min,
            i.digitization_priority,
            i.is_unique,
            i.rights_status,
            i.digital_file_exists,
            i.digitization_status,
            i.current_housing,
            i.misc_description,
            i.created_at
        FROM inventory i
        LEFT JOIN media_works w ON i.media_id = w.media_id
        GROUP BY i.media_id
        ORDER BY i.media_id ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def fetch_item_by_id(media_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM inventory WHERE media_id = ?", (media_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_works_for_media(media_id):
    """Fetches list of canonical work names associated with a media item."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT work_name FROM media_works WHERE media_id = ?", (media_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [row["work_name"] for row in rows]


def save_or_update_item(data_dict, selected_works, is_edit_mode):
    conn = get_db_connection()
    c = conn.cursor()

    try:
        if is_edit_mode:
            c.execute(
                """
                UPDATE inventory SET
                    physical_format = ?,
                    brand_stock = ?,
                    tape_length = ?,
                    media_case_label = ?,
                    item_title = ?,
                    date_on_label = ?,
                    production_reel_info = ?,
                    generation_level = ?,
                    collection_series = ?,
                    box_number = ?,
                    physical_condition = ?,
                    baking_flag = ?,
                    audio_track_info = ?,
                    estimated_runtime_min = ?,
                    digitization_priority = ?,
                    is_unique = ?,
                    rights_status = ?,
                    digital_file_exists = ?,
                    digitization_status = ?,
                    current_housing = ?,
                    misc_description = ?
                WHERE media_id = ?
            """,
                (
                    data_dict["physical_format"],
                    data_dict["brand_stock"],
                    data_dict["tape_length"],
                    data_dict["media_case_label"],
                    data_dict["item_title"],
                    data_dict["date_on_label"],
                    data_dict["production_reel_info"],
                    data_dict["generation_level"],
                    data_dict["collection_series"],
                    data_dict["box_number"],
                    data_dict["physical_condition"],
                    data_dict["baking_flag"],
                    data_dict["audio_track_info"],
                    data_dict["estimated_runtime_min"],
                    data_dict["digitization_priority"],
                    data_dict["is_unique"],
                    data_dict["rights_status"],
                    data_dict["digital_file_exists"],
                    data_dict["digitization_status"],
                    data_dict["current_housing"],
                    data_dict["misc_description"],
                    data_dict["media_id"],
                ),
            )
        else:
            c.execute(
                """
                INSERT INTO inventory (
                    media_id, physical_format, brand_stock, tape_length,
                    media_case_label, item_title, date_on_label,
                    production_reel_info, generation_level, collection_series, box_number,
                    physical_condition, baking_flag, audio_track_info, estimated_runtime_min,
                    digitization_priority, is_unique, rights_status, digital_file_exists,
                    digitization_status, current_housing, misc_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data_dict["media_id"],
                    data_dict["physical_format"],
                    data_dict["brand_stock"],
                    data_dict["tape_length"],
                    data_dict["media_case_label"],
                    data_dict["item_title"],
                    data_dict["date_on_label"],
                    data_dict["production_reel_info"],
                    data_dict["generation_level"],
                    data_dict["collection_series"],
                    data_dict["box_number"],
                    data_dict["physical_condition"],
                    data_dict["baking_flag"],
                    data_dict["audio_track_info"],
                    data_dict["estimated_runtime_min"],
                    data_dict["digitization_priority"],
                    data_dict["is_unique"],
                    data_dict["rights_status"],
                    data_dict["digital_file_exists"],
                    data_dict["digitization_status"],
                    data_dict["current_housing"],
                    data_dict["misc_description"],
                ),
            )

        # Update media_works junction table
        c.execute(
            "DELETE FROM media_works WHERE media_id = ?", (data_dict["media_id"],)
        )
        for work in selected_works:
            c.execute(
                "INSERT INTO media_works (media_id, work_name) VALUES (?, ?)",
                (data_dict["media_id"], work),
            )

        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def generate_next_id():
    df = fetch_inventory()
    if df.empty or "media_id" not in df.columns:
        return "GFD_AV_0001"

    ids = df["media_id"].dropna().tolist()
    nums = []
    for item in ids:
        if item.startswith("GFD_AV_"):
            try:
                nums.append(int(item.replace("GFD_AV_", "")))
            except ValueError:
                pass

    if not nums:
        return "GFD_AV_0001"

    return f"GFD_AV_{max(nums) + 1:04d}"


# Initialize DB & Load Canonical Works List
init_db()
canonical_works_list = load_canonical_works()

# -----------------------------------------------------------------------------
# NAVIGATION STATE
# -----------------------------------------------------------------------------
if "current_page" not in st.session_state:
    st.session_state.current_page = "main"

if "selected_media_id" not in st.session_state:
    st.session_state.selected_media_id = None

if "form_mode" not in st.session_state:
    st.session_state.form_mode = "create"


def navigate_to(page, mode="create", media_id=None):
    st.session_state.current_page = page
    st.session_state.form_mode = mode
    st.session_state.selected_media_id = media_id
    st.rerun()


# -----------------------------------------------------------------------------
# CONTROLLED OPTIONS
# -----------------------------------------------------------------------------
FORMAT_OPTIONS = [
    '1" Type C',
    "U-matic KCA",
    "Hi8",
    "miniDV",
    "BetaMax",
    "VHS",
    "CD",
    "DVD",
    "miniDisc",
    "DAT",
    "audio cassettes",
]

GENERATION_OPTIONS = [
    "Camera Original",
    "Master",
    "Sub-Master",
    "Dub / Copy",
    "Unknown",
]

CONDITION_OPTIONS = [
    "Mold",
    "Damaged Shell",
    "Broken Leader",
    "Flaking",
    "Odor",
    "Sticky-Shed Risk",
]

HOUSING_OPTIONS = [
    "GFD Studio / Archives",
    "MTS (Vendor Facility)",
    "In Transit",
    "LOC (Library of Congress)",
    "Other",
]

SERIES_OPTIONS = [
    "Series 1: Performance Recordings",
    "Series 2: Rehearsals & Workprints",
    "Series 3: Promotional & Media Interviews",
    "Series 4: Educational & Workshops",
    "Series 5: Special Events & Ceremonies",
    "Unassigned",
]

PRIORITY_OPTIONS = [
    "1 - High (Severe Risk / Unique)",
    "2 - Medium (Standard Preservation)",
    "3 - Low (Duplicate / Lower Value)",
    "4 - Do Not Digitize",
]

UNIQUENESS_OPTIONS = [
    "Unique Original",
    "Duplicate - Preferred Exemplar",
    "Duplicate - Secondary",
    "Unknown",
]

RIGHTS_OPTIONS = [
    "In Copyright - GFD Owned",
    "Third-Party Commercial Broadcaster",
    "Orphan Work / Unknown",
    "Public Domain",
]

DIGI_FILE_OPTIONS = [
    "No",
    "Yes - Derivative Only (MP4)",
    "Yes - Preservation Master (ProRes/MOV)",
]

DIGITIZATION_OPTIONS = ["Not digitized", "In process", "Digitized"]

BAKING_OPTIONS = ["No", "Suspected", "Yes"]

# -----------------------------------------------------------------------------
# PAGE 1: MAIN CATALOG TABLE
# -----------------------------------------------------------------------------
if st.session_state.current_page == "main":
    col1, col2 = st.columns([1, 5], vertical_alignment="center")

    with col1:
        logo_path = "/Users/tng/Documents/GFD/mediaLit/55_GFD_logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=400)
        else:
            st.write("🎭 **Garth Fagan Dance**")

    with col2:
        st.markdown(
            """
            <h1 style="margin-bottom: 0;">Garth Fagan Dance</h1>
            <p style="font-size: 1.25rem; color: #666; margin-top: 0;">
                AV Collection Catalog
            </p>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    st.caption(
        "Rapid physical inventory logging for grant submission and vendor tracking."
    )

    df = fetch_inventory()

    col1, col2, col3 = st.columns([2, 2, 4])

    with col1:
        if st.button("➕ Create New Entry", use_container_width=True, type="primary"):
            navigate_to("form", mode="create")

    with col2:
        edit_disabled = df.empty
        if st.button(
            "✏️ Edit Selected Row", use_container_width=True, disabled=edit_disabled
        ):
            selected_rows = (
                st.session_state.get("table_selection", {})
                .get("selection", {})
                .get("rows", [])
            )
            if selected_rows:
                selected_idx = selected_rows[0]
                selected_media_id = df.iloc[selected_idx]["media_id"]
                navigate_to("form", mode="edit", media_id=selected_media_id)
            else:
                st.warning(
                    "Please select a row from the table below before clicking Edit."
                )

    st.divider()

    if df.empty:
        st.info("No records in database. Click **Create New Entry** above to begin.")
    else:
        # Metrics Calculation
        total_items = len(df)
        total_runtime = (
            df["estimated_runtime_min"].sum()
            if "estimated_runtime_min" in df.columns
            else 0
        )
        total_hours = round(total_runtime / 60.0, 1) if total_runtime else 0
        high_priority = (
            len(df[df["digitization_priority"].str.startswith("1", na=False)])
            if "digitization_priority" in df.columns
            else 0
        )
        baking_req = (
            len(df[df["baking_flag"].isin(["Yes", "Suspected"])])
            if "baking_flag" in df.columns
            else 0
        )

        # Collection Statistics Header
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Media Items", total_items)
        m2.metric("Est. Total Content Hours", f"{total_hours} hrs")
        m3.metric("High Priority (Priority 1)", high_priority)
        m4.metric("Baking Required/Suspected", baking_req)

        st.markdown("### Physical Inventory Table")

        # Display Table with single-row selection
        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="table_selection",
        )

# -----------------------------------------------------------------------------
# PAGE 2: DATA ENTRY / EDIT FORM
# -----------------------------------------------------------------------------
elif st.session_state.current_page == "form":
    is_edit = st.session_state.form_mode == "edit"
    media_id_to_edit = st.session_state.selected_media_id

    existing = None
    existing_works = []

    if is_edit and media_id_to_edit:
        existing = fetch_item_by_id(media_id_to_edit)
        existing_works = fetch_works_for_media(media_id_to_edit)

    header_title = (
        f"✏️ Edit Record: {media_id_to_edit}"
        if is_edit
        else "➕ Create New Media Entry"
    )
    st.title(header_title)

    if st.button("⬅️ Cancel & Back to Table"):
        navigate_to("main")

    st.divider()

    # Field Value Fallbacks
    def_id = existing["media_id"] if existing else generate_next_id()
    def_format = (
        existing["physical_format"]
        if existing and existing["physical_format"] in FORMAT_OPTIONS
        else FORMAT_OPTIONS[0]
    )
    def_brand = existing["brand_stock"] if existing else ""
    def_length = existing["tape_length"] if existing else ""
    def_case = existing["media_case_label"] if existing else ""
    def_title = existing["item_title"] if existing else ""
    def_date = existing["date_on_label"] if existing else ""
    def_prod = existing["production_reel_info"] if existing else ""
    def_gen = (
        existing["generation_level"]
        if existing and existing["generation_level"] in GENERATION_OPTIONS
        else GENERATION_OPTIONS[0]
    )
    def_series = (
        existing["collection_series"]
        if existing and existing["collection_series"] in SERIES_OPTIONS
        else SERIES_OPTIONS[0]
    )
    def_box = existing["box_number"] if existing else ""
    def_baking = (
        existing["baking_flag"]
        if existing and existing["baking_flag"] in BAKING_OPTIONS
        else "No"
    )
    def_audio = existing["audio_track_info"] if existing else ""
    def_runtime = (
        float(existing["estimated_runtime_min"])
        if existing and existing["estimated_runtime_min"]
        else 60.0
    )
    def_prio = (
        existing["digitization_priority"]
        if existing and existing["digitization_priority"] in PRIORITY_OPTIONS
        else PRIORITY_OPTIONS[0]
    )
    def_unique = (
        existing["is_unique"]
        if existing and existing["is_unique"] in UNIQUENESS_OPTIONS
        else UNIQUENESS_OPTIONS[0]
    )
    def_rights = (
        existing["rights_status"]
        if existing and existing["rights_status"] in RIGHTS_OPTIONS
        else RIGHTS_OPTIONS[0]
    )
    def_file = (
        existing["digital_file_exists"]
        if existing and existing["digital_file_exists"] in DIGI_FILE_OPTIONS
        else DIGI_FILE_OPTIONS[0]
    )
    def_digi = (
        existing["digitization_status"]
        if existing and existing["digitization_status"] in DIGITIZATION_OPTIONS
        else "Not digitized"
    )
    def_housing = (
        existing["current_housing"]
        if existing and existing["current_housing"] in HOUSING_OPTIONS
        else HOUSING_OPTIONS[0]
    )
    def_desc = existing["misc_description"] if existing else ""

    # Pre-select valid existing canonical works for multiselect
    def_works = [w for w in existing_works if w in canonical_works_list]

    # Physical Condition multi-select parser
    def_conditions = []
    if existing and existing["physical_condition"]:
        def_conditions = [
            c.strip()
            for c in existing["physical_condition"].split(",")
            if c.strip() in CONDITION_OPTIONS
        ]

    with st.form("media_form", clear_on_submit=False):

        # --- SECTION 1 ---
        st.subheader("1. Archival Context & Location")
        c1, c2, c3 = st.columns(3)
        with c1:
            media_id = st.text_input(
                "Media ID (Primary Key)",
                value=def_id,
                disabled=is_edit,
                help="Locked in edit mode.",
            )
            collection_series = st.selectbox(
                "Collection / Series",
                SERIES_OPTIONS,
                index=SERIES_OPTIONS.index(def_series),
            )
        with c2:
            box_number = st.text_input(
                "Box / Storage Container Number",
                value=def_box,
                placeholder="e.g., Box 04, Shelf 2B",
            )
            current_housing = st.selectbox(
                "Current Location",
                HOUSING_OPTIONS,
                index=HOUSING_OPTIONS.index(def_housing),
            )
        with c3:
            digitization_status = st.selectbox(
                "Digitization Status",
                DIGITIZATION_OPTIONS,
                index=DIGITIZATION_OPTIONS.index(def_digi),
            )
            digital_file_exists = st.selectbox(
                "Digital File Already Exists?",
                DIGI_FILE_OPTIONS,
                index=DIGI_FILE_OPTIONS.index(def_file),
            )

        st.divider()

        # --- SECTION 2 ---
        st.subheader("2. Physical Format & Generation")
        c4, c5, c6 = st.columns(3)
        with c4:
            physical_format = st.selectbox(
                "Physical Format",
                FORMAT_OPTIONS,
                index=FORMAT_OPTIONS.index(def_format),
            )
            generation_level = st.selectbox(
                "Generation Level",
                GENERATION_OPTIONS,
                index=GENERATION_OPTIONS.index(def_gen),
            )
        with c5:
            brand_stock = st.text_input(
                "Brand / Stock",
                value=def_brand,
                placeholder="e.g., 3M 226, Sony KCA-60, Maxell XLII",
            )
            tape_length = st.text_input(
                "Tape Shell Capacity",
                value=def_length,
                placeholder="e.g., 60 min, T-120, 1200 ft",
            )
        with c6:
            estimated_runtime_min = st.number_input(
                "Estimated Content Runtime (Mins)",
                min_value=0.0,
                max_value=600.0,
                value=def_runtime,
                step=1e-2,
                help="Critical for grant budgeting and vendor cost estimation.",
            )

        st.divider()

        # --- SECTION 3 ---
        st.subheader("3. Label Transcriptions & Canonical Content")
        c7, c8 = st.columns(2)
        with c7:
            item_title = st.text_input(
                "Item Title / Label (as written) *",
                value=def_title,
                placeholder="Transcribe main tape label exactly",
            )

            # Autocomplete Canonical Works Multiselect
            selected_canonical_works = st.multiselect(
                "Canonical Performance / Work Name(s)",
                options=canonical_works_list,
                default=def_works,
                placeholder="Type title to search rep list (e.g., Prelude, Griot New York)...",
                help="Select one or more works associated with this media item.",
            )

            media_case_label = st.text_input(
                "Media Case Label",
                value=def_case,
                placeholder="Text written on outer box/slipcase if different",
            )
        with c8:
            date_on_label = st.text_input(
                "Date On Label",
                value=def_date,
                placeholder="e.g., 1994-11-12 or Nov 1994",
            )
            production_reel_info = st.text_input(
                "Production / Reel Info",
                value=def_prod,
                placeholder="e.g., Cam A, Show Run, Edited Master",
            )
            audio_track_info = st.text_input(
                "Audio Track Info",
                value=def_audio,
                placeholder="e.g., Ch1: Timecode, Ch2: Sync Audio",
            )

        st.divider()

        # --- SECTION 4 ---
        st.subheader("4. Grant Evaluation & Priority Assessment")
        c9, c10, c11 = st.columns(3)
        with c9:
            digitization_priority = st.selectbox(
                "Digitization Priority Rank",
                PRIORITY_OPTIONS,
                index=PRIORITY_OPTIONS.index(def_prio),
            )
            is_unique = st.selectbox(
                "Uniqueness / Exemplar Status",
                UNIQUENESS_OPTIONS,
                index=UNIQUENESS_OPTIONS.index(def_unique),
            )
        with c10:
            rights_status = st.selectbox(
                "Copyright & Usage Rights",
                RIGHTS_OPTIONS,
                index=RIGHTS_OPTIONS.index(def_rights),
            )
            baking_flag = st.selectbox(
                "Baking Flag",
                BAKING_OPTIONS,
                index=BAKING_OPTIONS.index(def_baking),
            )
        with c11:
            physical_condition = st.multiselect(
                "Physical Condition Issues",
                CONDITION_OPTIONS,
                default=def_conditions,
            )

        st.divider()

        # --- SECTION 5 ---
        st.subheader("5. Miscellaneous Description")
        misc_description = st.text_area(
            "Misc Notes & Inscriptions",
            value=def_desc,
            placeholder="Add extra notes on physical degradation, sticky shed indicators, or label inscriptions...",
        )

        submit_btn = st.form_submit_button(
            "Save Record", type="primary", use_container_width=True
        )

        if submit_btn:
            if not media_id or not item_title:
                st.error("Please provide both a Media ID and Item Title.")
            else:
                form_data = {
                    "media_id": media_id,
                    "physical_format": physical_format,
                    "brand_stock": brand_stock,
                    "tape_length": tape_length,
                    "media_case_label": media_case_label,
                    "item_title": item_title,
                    "date_on_label": date_on_label,
                    "production_reel_info": production_reel_info,
                    "generation_level": generation_level,
                    "collection_series": collection_series,
                    "box_number": box_number,
                    "physical_condition": ", ".join(physical_condition),
                    "baking_flag": baking_flag,
                    "audio_track_info": audio_track_info,
                    "estimated_runtime_min": estimated_runtime_min,
                    "digitization_priority": digitization_priority,
                    "is_unique": is_unique,
                    "rights_status": rights_status,
                    "digital_file_exists": digital_file_exists,
                    "digitization_status": digitization_status,
                    "current_housing": current_housing,
                    "misc_description": misc_description,
                }
                save_or_update_item(
                    form_data,
                    selected_works=selected_canonical_works,
                    is_edit_mode=is_edit,
                )
                st.success(f"Record {media_id} saved successfully!")
                navigate_to("main")
