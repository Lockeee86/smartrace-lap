// Dropbox functions
async function exportToDropbox() {
    const btn = document.getElementById('btn-dropbox-export');
    const originalText = btn.innerHTML;
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Uploading...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/export/dropbox');
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Successfully uploaded to Dropbox!', 'success');
            updateDropboxInfo(result);
        } else {
            showNotification(`❌ Upload failed: ${result.message}`, 'danger');
        }
    } catch (error) {
        showNotification(`❌ Upload error: ${error.message}`, 'danger');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function checkDropboxStatus() {
    try {
        const response = await fetch('/api/dropbox/status');
        const status = await response.json();
        
        updateDropboxStatusBadge(status);
        updateDropboxInfo(status);
        
        if (status.connected) {
            showNotification(`✅ ${status.message}`, 'success');
        } else {
            showNotification(`⚠️ ${status.message}`, 'warning');
        }
    } catch (error) {
        showNotification(`❌ Status check failed: ${error.message}`, 'danger');
    }
}

function updateDropboxStatusBadge(status) {
    const badge = document.getElementById('dropbox-status-badge');
    if (!badge) return;
    
    if (status.connected) {
        badge.innerHTML = '<span class="badge bg-success">Dropbox Connected</span>';
    } else {
        badge.innerHTML = '<span class="badge bg-secondary">Dropbox Offline</span>';
    }
}

function updateDropboxInfo(info) {
    const infoDiv = document.getElementById('dropbox-info');
    if (!infoDiv) return;
    
    if (info.connected && info.account_name) {
        infoDiv.innerHTML = `
            <div class="alert alert-success alert-sm">
                <strong>Account:</strong> ${info.account_name}<br>
                <strong>Email:</strong> ${info.email}<br>
                <strong>Folder:</strong> ${info.folder}
            </div>
        `;
    } else if (info.results) {
        const successCount = info.results.filter(r => r.success).length;
        const totalCount = info.results.length;
        
        let resultHtml = `
            <div class="alert alert-info alert-sm">
                <strong>Upload Results:</strong> ${successCount}/${totalCount} files<br>
                <strong>Folder:</strong> ${info.folder}<br><br>
                <strong>Files:</strong><br>
        `;
        
        info.results.forEach(result => {
            const icon = result.success ? '✅' : '❌';
            resultHtml += `${icon} ${result.file}<br>`;
        });
        
        resultHtml += '</div>';
        infoDiv.innerHTML = resultHtml;
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Auto-check Dropbox status on load
document.addEventListener('DOMContentLoaded', function() {
    // Check Dropbox status after 2 seconds
    setTimeout(checkDropboxStatus, 2000);
});
