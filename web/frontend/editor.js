let editor;

window.require(["vs/editor/editor.main"], function () {
    editor = monaco.editor.create(document.getElementById("editorContainer"), {
        value: `// Define points in 2D space
point p1 = (0.0, 0.0)
point p2 = (4.0, 0.0)
point p3 = (0.0, 3.0)

// Create a shape
complex triangle = [p1, p2, p3]

// Transform it
complex moved = translate(triangle, (5, 2))
complex scaled = scale(moved, 1.5)
`,
        language: "plaintext",
        theme: "vs-dark",
        automaticLayout: true
    });
});

document.getElementById("runBtn").addEventListener("click", async () => {
    const code = editor.getValue();
    const outputArea = document.getElementById("outputArea");

    outputArea.textContent = "Running...\n";

    try {
        const response = await fetch("/run_program", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ program: code })
        });

        const result = await response.json();

        if (!result.success) {
            outputArea.innerHTML = `<div class="output-card"><h3>Error</h3><pre>${result.error}</pre></div>`;
            return;
        }

        outputArea.innerHTML = "";
        
        // Render each complex stored in the environment
        for (const [name, complex] of Object.entries(result.complexes).reverse()) {
            const card = document.createElement("div");
            card.className = "output-card";

            const title = document.createElement("div");
            title.className = "output-card-title";
            title.textContent = `Complex: ${name}`;

            const row = document.createElement("div");
            row.className = "output-card-row";

            const cardInfo = document.createElement("div");
            cardInfo.className = "output-card-info";

            // Map coordinates for easy display
            const coordStr = Object.entries(complex.coords)
                .map(([v, pt]) => `${v}:(${pt[0]}, ${pt[1]})`).join(" | ");

            cardInfo.innerHTML = `
            <div class="row"><span class="label">Vertices</span><span>${Object.keys(complex.coords).join(", ")}</span></div>
            <div class="row"><span class="label">Coords</span><span>${coordStr}</span></div>
            <div class="row"><span class="label">Simplices</span><span>${complex.simplices.map(s => `[${s.join(",")}]`).join(" ")}</span></div>
            `;

            const renderBtn = document.createElement("button");
            renderBtn.textContent = "Render";
            renderBtn.className = "render-btn";
            renderBtn.addEventListener("click", () => {
                window.renderComplex3D(complex);
            });

            row.appendChild(cardInfo);
            row.appendChild(renderBtn);
            card.appendChild(title);
            card.appendChild(row);
            outputArea.appendChild(card);
        }
    } catch (err) {
        outputArea.innerHTML = `<div class="output-card"><h3>Network/Parse Error</h3><pre>${err}</pre></div>`;
    }
});