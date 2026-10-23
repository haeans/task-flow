fetch('/api/tasks') // 서버에 GET /api/tasks 요청을 보냅니다.
    .then(r => r.json()) // 응답을 JSON으로 변환합니다.
    .then(console.log) // 변환된 JSON 데이터를 콘솔에 출력합니다.

fetch('/api/tasks/id', { method: 'PATCH', // PATCH 요청을 보냅니다.
    headers: {
        'Content-Type': 'application/json'}, // 요청 헤더에 JSON 형식을 지정합니다.   
    body: JSON.stringify({ title: '바꿔 보는 실습' }) // 요청 본문에 JSON 데이터를 포함합니다.
}).then (r => console.log(r.status)) // 응답을 JSON으로 변환합니다.
