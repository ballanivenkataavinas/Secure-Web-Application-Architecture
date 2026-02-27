const API = "https://secure-web-application-architecture-production.up.railway.app";

/* =========================
   PARTICLES (ALWAYS WORKING)
========================= */
function loadParticlesDark() {
    tsParticles.load("tsparticles", {
        particles: {
            color: { value: "#ffffff" },
            links: { enable: true, color: "#ffffff", opacity: 0.4 },
            number: { value: 60 },
            size: { value: 3 },
            move: { enable: true, speed: 2 }
        },
        interactivity: {
            events: { onHover: { enable: true, mode: "grab" } },
            modes: { grab: { distance: 200, links: { opacity: 1 } } }
        },
        background: { color: "transparent" }
    });
}

function loadParticlesLight() {
    tsParticles.load("tsparticles", {
        particles: {
            color: { value: "#222222" },
            links: { enable: true, color: "#444444", opacity: 0.6 },
            number: { value: 60 },
            size: { value: 3 },
            move: { enable: true, speed: 2 }
        },
        interactivity: {
            events: { onHover: { enable: true, mode: "grab" } },
            modes: { grab: { distance: 200, links: { opacity: 1 } } }
        },
        background: { color: "transparent" }
    });
}

function applyParticlesByTheme() {
    if (document.body.classList.contains("light-mode")) {
        loadParticlesLight();
    } else {
        loadParticlesDark();
    }
}

applyParticlesByTheme();

/* =========================
   FLOATING EMOJIS
========================= */
function createFloatingEmojis() {
    const emojis = ["🛡","💻","🔐","⚠","🚨","👾","🤖","🔥"];
    emojis.forEach(e => {
        for(let i = 0; i < 4; i++){
            let s = document.createElement("span");
            s.className = "floating";
            s.innerText = e;
            s.style.left = Math.random()*100 + "vw";
            s.style.animationDuration = (8 + Math.random()*10) + "s";
            s.style.fontSize = (18 + Math.random()*10) + "px";
            document.body.appendChild(s);
        }
    });
}
createFloatingEmojis();

/* =========================
   GLOBE (LOGIN ONLY)
========================= */
let globeStarted = false;
let renderer, scene, camera, Globe;

function initGlobe() {
    if (globeStarted) return;
    globeStarted = true;

    const container = document.getElementById("globeContainer");
    container.classList.remove("hidden");
    container.innerHTML = "";

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(
        60,
        window.innerWidth / window.innerHeight,
        0.1,
        2000
    );
    camera.position.z = 300;

    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 1);
    scene.add(ambientLight);

    Globe = new ThreeGlobe()
        .globeImageUrl("//unpkg.com/three-globe/example/img/earth-dark.jpg")
        .bumpImageUrl("//unpkg.com/three-globe/example/img/earth-topology.png")
        .arcColor(() => "red")
        .arcAltitude(0.25)
        .arcDashLength(0.4)
        .arcDashGap(2)
        .arcDashAnimateTime(2000);

    const arcsData = [...Array(40)].map(() => ({
        startLat: Math.random()*180-90,
        startLng: Math.random()*360-180,
        endLat: Math.random()*180-90,
        endLng: Math.random()*360-180
    }));

    Globe.arcsData(arcsData);
    scene.add(Globe);

    function animate() {
        requestAnimationFrame(animate);
        Globe.rotation.y += 0.0015;
        renderer.render(scene, camera);
    }
    animate();
}

/* =========================
   PAGE SWITCH
========================= */
function hideAll(){
    ["landingSection","registerSection","loginSection","dashboardSection"]
    .forEach(id=>document.getElementById(id).classList.add("hidden"));
    document.getElementById("globeContainer").classList.add("hidden");
}

function showLogin(){
    hideAll();
    document.getElementById("loginSection").classList.remove("hidden");
    initGlobe();
}

function showRegister(){
    hideAll();
    document.getElementById("registerSection").classList.remove("hidden");
}

function showDashboard(){
    hideAll();
    document.getElementById("dashboardSection").classList.remove("hidden");
}

function logout(){
    localStorage.removeItem("token");
    localStorage.removeItem("is_admin");
    document.getElementById("adminBtn").style.display = "none";
    hideAll();
    document.getElementById("landingSection").classList.remove("hidden");
}

/* =========================
   PASSWORD TOGGLE
========================= */
function togglePassword(id,icon){
    const input=document.getElementById(id);
    input.type=input.type==="password"?"text":"password";
    icon.innerText=input.type==="password"?"👁":"🙈";
}

/* =========================
   PASSWORD STRENGTH
========================= */
function checkStrength(){
    const p=document.getElementById("regPassword").value;
    const bar=document.getElementById("strengthBar");

    let score=0;

    const checks=[
        p.length>=8,
        /[A-Z]/.test(p),
        /[a-z]/.test(p),
        /\d/.test(p),
        /[!@#$%^&*(),.?":{}|<>]/.test(p)
    ];

    const ids=[
        "rule-length","rule-upper","rule-lower",
        "rule-number","rule-special"
    ];

    checks.forEach((valid,i)=>{
        const el=document.getElementById(ids[i]);
        if(valid){
            el.innerHTML="✅ "+el.innerText.substring(2);
            el.style.color="limegreen";
            score++;
        } else {
            el.innerHTML="❌ "+el.innerText.substring(2);
            el.style.color="red";
        }
    });

    bar.className="strength-bar";
    if(score<=2) bar.classList.add("weak");
    else if(score<=4) bar.classList.add("medium");
    else bar.classList.add("strong");
}

/* =========================
   DARK MODE
========================= */
document.getElementById("themeToggle").onclick = () => {
    document.body.classList.toggle("light-mode");
    applyParticlesByTheme();
};

/* =========================
   BACKEND CONNECTION
========================= */

/* REGISTER */
async function register() {
    const username = document.getElementById("regUsername").value;
    const password = document.getElementById("regPassword").value;

    if (!username || !password) {
        alert("Please fill all fields");
        return;
    }

    try {
        const response = await fetch(
            `${API}/register?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
            { method: "POST" }
        );

        const data = await response.json();

        if (response.ok) {
            alert("Registered Successfully ✅");
            showLogin();
        } else {
            alert(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
        }

    } catch (error) {
        console.error(error);
        alert("Server not running");
    }
}

/* LOGIN */
async function login() {

    const username = document.getElementById("loginUsername").value;
    const password = document.getElementById("loginPassword").value;

    if (!username || !password) {
        alert("Please fill all fields");
        return;
    }

    try {

        const response = await fetch(
            `${API}/login?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
            { method: "POST" }
        );

        // ✅ RATE LIMIT ALERT
        if (response.status === 429) {
            alert("Too many requests. Try again later.");
            return;
        }

        const data = await response.json();

        if (response.ok) {

            localStorage.setItem("token", data.access_token);

            // ✅ STORE ADMIN ROLE
            localStorage.setItem("is_admin", data.is_admin);

            // ✅ SHOW / HIDE ADMIN BUTTON
            if (data.is_admin === true) {
                document.getElementById("adminBtn").style.display = "inline-block";
            } else {
                document.getElementById("adminBtn").style.display = "none";
            }

            alert("Login successful 🚀");
            showDashboard();

        } else {
            alert(data.detail);
        }

    } catch (error) {
        console.error(error);
        alert("Server not running");
    }
}

/* ANALYZE */
async function analyzeMessage() {

    const message = document.getElementById("message").value;
    const token = localStorage.getItem("token");

    if (!message) {
        alert("Please enter a message");
        return;
    }

    if (!token) {
        alert("Please login first");
        return;
    }

    try {

        const response = await fetch(`${API}/analyze`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                text: message,
                user_id: "temp"
            })
        });

        const data = await response.json();

        if (!response.ok) {
            alert(data.detail);
            return;
        }

        // ✅ FIXED POSITION
        if (data.warning) {
            alert(data.warning);
        }

        document.getElementById("result").classList.remove("hidden");
        document.getElementById("risk").innerText = data.risk_level;
        document.getElementById("score").innerText = data.score;
        document.getElementById("action").innerText = data.action;

        document.getElementById("riskMeter").style.width =
            Math.min(data.score * 10, 100) + "%";

    } catch (error) {
        console.error(error);
        alert("Server error");
    }
}

/* ✅ ADMIN BUTTON REDIRECT */
document.getElementById("adminBtn").addEventListener("click", function () {
    window.location.href = "admin_dashboard.html";
});