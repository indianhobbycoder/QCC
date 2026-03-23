document.addEventListener('DOMContentLoaded', () => {
  const payloadNode = document.getElementById('dashboard-data');
  if (!payloadNode || typeof Chart === 'undefined') return;

  const agentTrends = JSON.parse(payloadNode.dataset.agentTrends || '[]');
  const ctx = document.getElementById('agentTrendChart');
  if (ctx) {
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: agentTrends.map(item => item.label),
        datasets: [{
          label: 'Average Score',
          data: agentTrends.map(item => item.value),
          backgroundColor: '#0d6efd'
        }]
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true, max: 100 } }
      }
    });
  }
});
