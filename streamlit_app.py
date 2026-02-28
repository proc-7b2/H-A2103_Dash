import streamlit as st
from github import Github
import json
import time
import base64
import requests
import streamlit as st
import streamlit_authenticator as stauth

# --- 1. AUTHENTICATION SETUP ---
auth_secrets = st.secrets["auth"]
config = {
    "credentials": {
        "usernames": {
            u: dict(v) for u, v in auth_secrets["credentials"]["usernames"].items()
        }
    },
    "cookie": dict(auth_secrets["cookie"])
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Render Login (location='main' keeps it centered and clean)
authenticator.login(location='main')

# --- 2. THE PROTECTIVE GATE ---
if st.session_state["authentication_status"]:

# --- HELPER: FETCH ROBLOX DATA ---
    def get_roblox_bundle_info(bundle_id):
        try:
            # 1. Get Name
            details_url = f"https://catalog.roblox.com/v1/bundles/{bundle_id}/details"
            details_res = requests.get(details_url).json()
            name = details_res.get("name", "Unknown Bundle")

            # 2. Get Thumbnail
            thumb_url = f"https://thumbnails.roblox.com/v1/bundles/thumbnails?bundleIds={bundle_id}&size=420x420&format=Png&isCircular=false"
            thumb_res = requests.get(thumb_url).json()
            img_url = thumb_res['data'][0]['imageUrl'] if 'data' in thumb_res else None
            
            return name, img_url
        except:
            return "Bundle Metadata Error", None

    # --- CONFIG ---
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"] 
    SOURCE_REPO_NAME = "proc-7b2/Rd-3245_Misc"
    TARGET_REPO_NAME = "proc-7b2/H-3242AA"
    CLEANUP_WORKFLOW = "Cleanup.yml" 
    SEPARATE_WORKFLOW = "Separate.yml"

    g = Github(GITHUB_TOKEN)
    source_repo = g.get_repo(SOURCE_REPO_NAME)
    target_repo = g.get_repo(TARGET_REPO_NAME)

    # --- UI STATE ---
    if "status" not in st.session_state: st.session_state.status = 1 
    if "queue" not in st.session_state: st.session_state.queue = []

    # --- SIDEBAR NAVIGATION ---
    st.sidebar.title("🐜 Ant Control")

   
              
    st.sidebar.markdown("---")

    # Manual Override for Navigation
    page_labels = {
        1: "📂 1. Selection",
        2: "🚚 2. Transferring",
        3: "🤖 3. Blender Cleanup",
        4: "🏗️ 4. Monitoring",
        5: "🖌️ 5. Separation",
        6: "🏗️ 6. Procedural Pipeline"
    }

    st.session_state.status = st.sidebar.radio(
        "Jump to Step:", 
        options=list(page_labels.keys()), 
        format_func=lambda x: page_labels[x],
        index=list(page_labels.keys()).index(st.session_state.status)
    )



    
    st.sidebar.markdown("---")

    if st.sidebar.button("♻️ Reset App State"):
        st.session_state.status = 1
        st.session_state.queue = []
        st.rerun()


    st.markdown("""
    <style>
    /* --- 1. GLOBAL BUTTON TEXT COLOR --- */
    /* This changes the text color for ALL buttons */
    div.stButton > button p {
        color: white;
        font-weight: 600;
    }

    /* --- 2. LOGOUT BUTTON STYLING (RED) --- */
    /* Target buttons in the sidebar that contain the word "Logout" */
    section[data-testid="stSidebar"] .stButton button:has(div p:contains("Logout")) {
        background-color: #3e1212; /* Dark red base */
        color: #ff7b72;           /* Light red text */
        border: 1px solid #6e2e2e;
    }

    /* HOVER STATE for Logout */
    section[data-testid="stSidebar"] .stButton button:has(div p:contains("Logout")):hover {
        background-color: #ff4b4b !important; /* Bright red on hover */
        color: white !important;             /* White text on hover */
        border-color: #ff3333 !important;
    }

    /* --- 3. PRIMARY ACTION BUTTONS (The Red/Pink ones) --- */
    /* Target buttons you've set to type="primary" */
    div.stButton > button[kind="primary"] {
        background-color: #ff5f5f; 
        color: white;
        border: none;
    }

    /* HOVER STATE for Primary */
    div.stButton > button[kind="primary"]:hover {
        background-color: #ff3333; /* Darker/Brighter red */
        color: #ffffff;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4); /* Adds a glow effect */
    }

    /* --- 4. SECONDARY BUTTONS (Reset App State) --- */
    div.stButton > button[kind="secondary"] {
        background-color: #161b22;
        border: 1px solid #30363d;
    }

    div.stButton > button[kind="secondary"]:hover {
        border-color: #58a6ff; /* Blue border on hover */
        color: #58a6ff !important;
    }
    </style>
    """, unsafe_allow_html=True)

    
    st.sidebar.markdown("<br>" * 10, unsafe_allow_html=True)
    st.sidebar.markdown("---")

    authenticator.logout('🔻 Logout', 'sidebar')     

    # --- CSS ---
    st.markdown("""
        <style>
        .model-card { background: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 8px; margin-bottom: 5px; }
        .status-tag { font-size: 0.8em; padding: 2px 8px; border-radius: 10px; }
        .tag-error { background: #442323; color: #ff7b72; }
        .tag-success { background: #234423; color: #7ee787; }
        </style>
    """, unsafe_allow_html=True)

    # --- UTILITIES ---
    def get_model_status(model_id):
        try:
            content = source_repo.get_contents(f"downloads/{model_id}/status.json").decoded_content
            data = json.loads(content)
            data['img_url'] = f"https://raw.githubusercontent.com/{SOURCE_REPO_NAME}/main/downloads/{model_id}/error_screenshot.png"
            return data
        except: return None

    # --- PHASE 1: SELECTION ---
    if st.session_state.status == 1:
        st.title("📂 Step 1: Select Models")
        try:
            folders = [f.name for f in source_repo.get_contents("downloads") if f.type == "dir"]
        except: folders = []

        select_all = st.checkbox("Select All")
        selected_this_run = []
        
        for model in folders:
            status = get_model_status(model)
            with st.container():
                st.markdown('<div class="model-card">', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                if c1.checkbox("", value=select_all, key=f"sel_{model}"):
                    selected_this_run.append(model)
                
                if status:
                    color = "tag-success" if status['status'] == "Success" else "tag-error"
                    c2.markdown(f"📦 **{model}** <span class='status-tag {color}'>{status['status']}</span>", unsafe_allow_html=True)
                    if status['status'] == "Error":
                        with c3:
                            with st.popover("⚠️ Info"):
                                st.write(f"**Message:** {status['message']}")
                                st.image(status['img_url'])
                else:
                    c2.write(f"📦 {model}")
                st.markdown('</div>', unsafe_allow_html=True)

        if st.button("🚀 MOVE TO INPUT", type="primary", use_container_width=True):
            if selected_this_run:
                st.session_state.queue = selected_this_run
                st.session_state.status = 2
                st.rerun()

    # --- PHASE 2: MOVING ---
    elif st.session_state.status == 2:
        st.title("🚚 Step 2: Transferring Files")
        if st.session_state.queue:
            current = st.session_state.queue[0]
            st.info(f"Transferring: {current}")
            try:
                files = source_repo.get_contents(f"downloads/{current}")
                pbar = st.progress(0)
                for i, f in enumerate(files):
                    file_data = base64.b64decode(f.content)
                    target_repo.create_file(path=f"input/{current}/{f.name}", message=f"Move {current}", content=file_data, branch="main")
                    source_repo.delete_file(f.path, message=f"Cleanup {current}", sha=f.sha)
                    pbar.progress((i+1)/len(files))
                
                st.session_state.queue.pop(0)
                if not st.session_state.queue: st.session_state.status = 3
                st.rerun()
            except Exception as e:
                st.error(f"Transfer Failed: {e}")
                if st.button("Skip Model"):
                    st.session_state.queue.pop(0)
                    st.rerun()
        else:
            st.success("Transfer queue empty! Move to Step 3.")

    # --- PHASE 3: BLENDER CLEANUP ---
    elif st.session_state.status == 3:
        st.title("🤖 Step 3: Blender Cleanup")
        try:
            ready = [f.name for f in target_repo.get_contents("input") if f.type == "dir"]
        except: ready = []

        if ready:
            st.write(f"Models in `input/` ready for processing:")
            for m in ready: st.code(f"📍 {m}")
            if st.button("🔥 START CLEANUP WORKFLOW", type="primary", use_container_width=True):
                workflow = target_repo.get_workflow(CLEANUP_WORKFLOW)
                for m in ready:
                    workflow.create_dispatch(ref="main", inputs={"model_id": m})
                st.session_state.status = 4
                st.rerun()
        else:
            st.info("No models found in `input/` folder.")

    # --- PHASE 4: MONITORING ---
    elif st.session_state.status == 4:
        st.title("🏗️ Step 4: Monitoring Actions")
        st.info("Cleanup in progress. Check logs below.")
        st.link_button("📊 Open GitHub Actions Tab", f"https://github.com/{TARGET_REPO_NAME}/actions", use_container_width=True)
        
        st.divider()
        st.write("Once files appear in `output/CleanedFiles/`, move to Separation.")
        if st.button("🖌️ GO TO SEPARATION STEP", use_container_width=True):
            st.session_state.status = 5
            st.rerun()

    # --- PHASE 5: SEPARATION (NEW) ---
    # --- PHASE 5: SEPARATION ---
    elif st.session_state.status == 5:
        st.title("🖌️ Step 5: Mesh Separation")
        
        # Check for cleaned files in the target repo
        naming_map = [
            "UpperTorso_Geo", "LowerTorso_Geo", "LeftUpperArm_Geo", "LeftLowerArm_Geo",
            "LeftHand_Geo", "RightUpperArm_Geo", "RightLowerArm_Geo", "RightHand_Geo",
            "LeftUpperLeg_Geo", "LeftLowerLeg_Geo", "LeftFoot_Geo", "RightUpperLeg_Geo",
            "RightLowerLeg_Geo", "RightFoot_Geo", "Head_Geo"
        ]

        try:
            cleaned_folders = [f.name for f in target_repo.get_contents("output/CleanedFiles") if f.type == "dir"]
        except:
            cleaned_folders = []
        
        if not cleaned_folders:
            st.warning("No cleaned models found in `output/CleanedFiles/`. Complete Step 3 first.")
        else:
            selected_model = st.selectbox("Select Model to Process:", cleaned_folders)
            
            # Create Tabs for the two modes
            tab_manual, tab_auto = st.tabs(["🛠️ Manual Separation", "🤖 Automatic (AI)"])

            # --- MANUAL OPTION ---
            with tab_manual:

                # --- THE MAP BUTTON ---
                with st.popover("🗺️ View Naming Map", use_container_width=True):
                    st.markdown("### 📋 Required Part Names")
                    st.write("Use these exact names (or indices) when exporting from Blender:")
                    
                    # Create a list with numbers
                    map_data = [{"Index": i, "Part Name": name} for i, name in enumerate(naming_map)]
                    st.table(map_data)


                # --- UPDATED DOWNLOAD SECTION ---
                st.markdown("### 📥 1. Download Cleaned File")
                st.write(f"Download the model, separate parts in Blender local, and rename them.")

                model_files = target_repo.get_contents(f"output/CleanedFiles/{selected_model}")

                for gf in model_files:
                    if gf.type == "file":
                        # This fetches the actual file content from GitHub
                        file_content = gf.decoded_content 
                        
                        st.download_button(
                            label=f"📥 Download {gf.name}",
                            data=file_content,
                            file_name=gf.name,
                            mime="application/octet-stream", # This mime type forces a download
                            use_container_width=True
                        )

                st.divider()

                st.markdown("### 📤 2. Upload Separated Parts")
                uploaded_files = st.file_uploader(
                    "Upload your separated .glb or .obj files", 
                    accept_multiple_files=True,
                    help="Upload all parts of the model here."
                )

                if uploaded_files:
                    if st.button(f"✅ Commit {len(uploaded_files)} Parts to GitHub", type="primary"):
                        progress_text = "Uploading parts..."
                        my_bar = st.progress(0, text=progress_text)
                        
                        try:
                            for i, uploaded_file in enumerate(uploaded_files):
                                # Read file content
                                bytes_data = uploaded_file.getvalue()
                                
                                # Define path: final_output/model_id/filename.glb
                                path = f"Seperated_Bundles/{selected_model}/{uploaded_file.name}"
                                
                                # Upload to Target Repo
                                target_repo.create_file(
                                    path=path,
                                    message=f"Manual separation upload for {selected_model}",
                                    content=bytes_data,
                                    branch="main"
                                )
                                my_bar.progress((i + 1) / len(uploaded_files))
                            
                            st.success(f"Successfully uploaded {len(uploaded_files)} parts to `Seperated_Bundles/{selected_model}/`!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Upload failed: {e}")


                # --- DANGER ZONE (Cleanup) ---
                st.markdown("<br><br>", unsafe_allow_html=True)
                with st.expander("🚨 Danger Zone (Cleanup)"):
                    col1, col2 = st.columns(2)
                    
                    # Option A: Clear Current
                    with col1:
                        st.write("**Specific Cleanup**")
                        if st.button(f"🗑️ Clear {selected_model}", use_container_width=True):
                            with st.spinner("Deleting..."):
                                files = target_repo.get_contents(f"output/CleanedFiles/{selected_model}")
                                for f in files:
                                    if f.type == "file":
                                        target_repo.delete_file(f.path, "Manual Cleanup", f.sha)
                                st.rerun()
                    
                    # Option B: Clear All
                    with col2:
                        st.write("**Mass Cleanup**")
                        confirm_all = st.checkbox("Confirm Clear ALL")
                        if st.button("🔥 DELETE EVERYTHING", use_container_width=True, disabled=not confirm_all):
                            with st.spinner("Wiping CleanedFiles folder..."):
                                try:
                                    # Get all folders in CleanedFiles
                                    all_folders = target_repo.get_contents("output/CleanedFiles")
                                    for folder in all_folders:
                                        if folder.type == "dir":
                                            # Get files in each folder and delete
                                            inner_files = target_repo.get_contents(folder.path)
                                            for f in inner_files:
                                                target_repo.delete_file(f.path, "Mass Cleanup", f.sha)
                                    st.success("All cleaned files wiped!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

            # --- AUTOMATIC OPTION ---
            with tab_auto:
                st.markdown("""
                    <div style="text-align: center; padding: 50px; border: 2px dashed #30363d; border-radius: 15px; background: #0d1117;">
                        <h2 style="color: #58a6ff;">🚀 Coming Soon!</h2>
                        <p style="color: #8b949e;">Our automated Three.js & AI-assisted limb separation tool is currently in development.</p>
                        <div style="font-size: 50px;">🤖🏗️✨</div>
                    </div>
                """, unsafe_allow_html=True)


    # --- PHASE 6: PROCEDURAL PIPELINE ---
    elif st.session_state.status == 6:
        st.title("🏗️ Step 6: Procedural Pipeline")
        
        try:
            ready_bundles = [f.name for f in target_repo.get_contents("Seperated_Bundles") if f.type == "dir"]
        except:
            ready_bundles = []

        if not ready_bundles:
            st.warning("No bundles found in `Seperated_Bundles/`.")
        else:
            selected_bundle = st.selectbox("Select Bundle ID to Automate:", ready_bundles)
            
            if selected_bundle:
                # Fetch metadata
                b_name, b_img = get_roblox_bundle_info(selected_bundle)
                
                # Display Header
                st.markdown(f"### 🏷️ {b_name}")
                
                # Use a wider column for the image (0.6 means 60% of the width)
                col_img, col_info = st.columns([0.6, 0.4])
                
                with col_img:
                    if b_img:
                        # use_container_width makes it fill the 60% column
                        st.image(b_img, use_container_width=True)
                    else:
                        st.info("No thumbnail available for this ID.")
                
                with col_info:
                    st.markdown(f"**Bundle ID:** `{selected_bundle}`")
                    st.success("Files Verified ✅")
                    st.write("Ready for procedural rigging, skinning, and cage fitting.")

            st.divider()
            
            # Style Selection
            st.markdown("### 🧬 Choose Automation Style")
            style_choice = st.radio(
                "Which template should be applied?",
                ["Humanoid", "Four Legs", "Chibi"],
                captions=["Standard 15-part Rig", "Quadruped Rig", "Proportional Chibi Rig"]
            )

            style_map = {
                "Humanoid": "humanoid_std",
                "Four Legs": "quadruped_std",
                "Chibi": "humanoid_chibi"
            }

            if st.button(f"🚀 RUN PIPELINE", type="primary", use_container_width=True):
                with st.spinner(f"Processing {b_name}..."):
                    try:
                        workflow = target_repo.get_workflow("Pipeline.yml")
                        workflow.create_dispatch(
                            ref="main", 
                            inputs={
                                "model_id": selected_bundle,
                                "style": style_map[style_choice],
                                "bundle_name": b_name
                            }
                        )
                        st.success(f"Pipeline dispatched!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Failed to start: {e}")

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.info('Please log in to access H-A2103')
