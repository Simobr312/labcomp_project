window.require(["vs/editor/editor.main"], function () {
    // 1. Create the data models (the "files")
    const dslModel = monaco.editor.createModel(
`// Define points in 3D space
point A = (0, 0, 0)
point B = (2 , 0 , 0)
point C = (1 , 1.732 , 0)
point D = (1 , 0.577 , 1.633)

complex tetrahedron = translate(scale([A , B , C , D ], 4), (0, 0, 1))

complex tetrahedron_rotated = rotate(tetrahedron, 60) 
`, 
        "plaintext"
    );

    const imgqlModel = monaco.editor.createModel(
    `// Write your PolyLogicA queries here
// 2. Bind the atomic propositions to your JSON atoms
let t1 = ap("tetrahedron")
let t2 = ap("tetrahedron_rotated")

let intersection = t1 & t2

save "int" intersection 
`, 
        "plaintext"
    );

    // 2. Initialize the single editor instance, starting with the DSL model
    const editor = monaco.editor.create(document.getElementById("editorContainer"), {
        model: dslModel,
        theme: "vs-dark",
        automaticLayout: true
    });

    // 3. Attach Tab Switching Logic HERE (Guarantees editor is ready)
    const tabDsl = document.getElementById("tabDsl");
    const tabImgql = document.getElementById("tabImgql");

    tabDsl.addEventListener("click", () => {
        editor.setModel(dslModel);
        tabDsl.classList.add("active");
        tabImgql.classList.remove("active");
        editor.focus(); // Snap focus back to the editor
    });

    tabImgql.addEventListener("click", () => {
        editor.setModel(imgqlModel);
        tabImgql.classList.add("active");
        tabDsl.classList.remove("active");
        editor.focus();
    });

    // 4. Expose functions to get values so the external buttons can read them safely
    window.getDslCode = () => dslModel.getValue();
    window.getImgqlCode = () => imgqlModel.getValue();
});

// ---------------------------------------------------------
// Run DSL & Render
// ---------------------------------------------------------
document.getElementById("runBtn").addEventListener("click", async () => {
    // Prevent running if Monaco hasn't loaded yet
    if (typeof window.getDslCode !== "function") {
        console.warn("Editor is still loading...");
        return; 
    }

    const code = window.getDslCode(); 
    const runBtn = document.getElementById("runBtn");
    const originalText = runBtn.textContent;
    runBtn.textContent = "Rendering...";

    try {
        const response = await fetch("/run_program", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ program: code })
        });

        const result = await response.json();

        if (!result.success) {
            alert("Error compiling DSL:\n" + result.error);
            return;
        }

        if (window.renderEnvironment3D) {
            window.renderEnvironment3D(result.complexes);
        }
    } catch (err) {
        alert("Network/Parse Error: " + err.message);
    } finally {
        runBtn.textContent = originalText;
    }
});

// ---------------------------------------------------------
// Run PolyLogicA (.imgql) Checker
// ---------------------------------------------------------
document.getElementById("runCheckerBtn").addEventListener("click", async () => {
    // Prevent running if Monaco hasn't loaded yet
    if (typeof window.getImgqlCode !== "function" || typeof window.getDslCode !== "function") {
        console.warn("Editor is still loading...");
        return; 
    }

    // Grab both contexts safely from the models
    const queryCode = window.getImgqlCode();
    const dslCode = window.getDslCode();
    
    const checkerOutputArea = document.getElementById("checkerOutputArea");
    const runCheckerBtn = document.getElementById("runCheckerBtn");
    const originalText = runCheckerBtn.textContent;
    
    runCheckerBtn.textContent = "Checking...";
    checkerOutputArea.innerHTML = "<div class='output-card' style='color:#ccc;'>Running PolyLogicA...</div>";

    try {
        // FIXED: Pointing to the correct API endpoint route
        const response = await fetch("/run_polylogica", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            // FIXED: Passing both payload requirements to server.py
            body: JSON.stringify({ 
                program: dslCode,
                query: queryCode 
            })
        });

        const result = await response.json();

        if (!result.success) {
            checkerOutputArea.innerHTML = `<div class="output-card"><h3 style="color: #ff5555; margin:0 0 10px 0;">Error</h3><pre style="margin:0;">${result.error}</pre></div>`;
            return;
        }

        checkerOutputArea.innerHTML = "";
        
        for (const [propName, values] of Object.entries(result.properties)) {
            const card = document.createElement("div");
            card.className = "output-card";

            const title = document.createElement("h3");
            title.style.margin = "0 0 10px 0";
            title.textContent = `Property: ${propName}`;

            const valuesDisplay = document.createElement("div");
            valuesDisplay.textContent = `Result: ${values.join(", ")}`;

            const drawBtn = document.createElement("button");
            drawBtn.textContent = "Draw Result";
            drawBtn.addEventListener("click", () => {
                console.log(`Drawing result for ${propName}...`);
                window.drawCheckerResult(propName, values); 
            });

            card.appendChild(title);
            card.appendChild(valuesDisplay);
            card.appendChild(drawBtn);
            checkerOutputArea.appendChild(card);
        }
    } catch (err) {
        checkerOutputArea.innerHTML = `<div class="output-card"><h3 style="color: #ff5555; margin:0 0 10px 0;">Network/Parse Error</h3><pre style="margin:0;">${err.message}</pre></div>`;
    } finally {
        runCheckerBtn.textContent = originalText;
    }
});
