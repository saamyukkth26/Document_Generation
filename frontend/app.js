const btn = document.getElementById('generate')
const status = document.getElementById('status')
const downloadDiv = document.getElementById('download')

btn.addEventListener('click', async () => {
  status.textContent = ''
  downloadDiv.innerHTML = ''
  const path = document.getElementById('path').value.trim()
  if (!path) {
    status.textContent = 'Please enter a folder path.'
    return
  }
  status.textContent = 'Generating...'
  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path})
    })
    if (!res.ok) {
      const err = await res.json()
      status.textContent = 'Error: ' + (err.detail || res.statusText)
      return
    }
    const data = await res.json()
    status.textContent = 'Generation complete.'
    const url = data.download_url
    const a = document.createElement('a')
    a.href = url
    a.textContent = 'Download HLD'
    a.className = 'download-link'
    downloadDiv.appendChild(a)
  } catch (e) {
    status.textContent = 'Error: ' + e.message
  }
})
