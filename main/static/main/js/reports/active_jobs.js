
async function loadJobs(){
    try{
        const response = await fetch("/api/jobs/");
        const data = await response.json();

        const list = document.getElementById("jobList");
        const empty = document.getElementById("emptyMsg");

        list.innerHTML = "";

        if(data.length === 0){
            empty.style.display = "block";
            return;
        }

        empty.style.display = "none";

        data.forEach(job => {
            const li = document.createElement("li");
            li.innerHTML = `
                <a href="/jobs/${job.id}/">
                    <strong>${job.title}</strong>
                    <div class="company">${job.company}</div>
                </a>
            `;
            list.appendChild(li);
        });

    }catch(error){
        console.error("Error loading jobs:", error);
    }
}

/* Initial load */
loadJobs();

/* Auto refresh every 5 seconds (near real-time) */
setInterval(loadJobs, 5000);