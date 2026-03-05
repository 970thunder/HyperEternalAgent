<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Settings</h3>
        <button class="btn btn-icon btn-ghost" @click="close">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="modal-body">
        <!-- Appearance -->
        <div class="settings-section">
          <h4>Appearance</h4>
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Theme</span>
              <span class="setting-description">Choose your preferred color scheme</span>
            </div>
            <div class="setting-control">
              <button
                v-for="theme in themes"
                :key="theme.id"
                class="theme-btn"
                :class="{ active: uiStore.theme === theme.id }"
                @click="uiStore.setTheme(theme.id)"
              >
                {{ theme.icon }}
                {{ theme.name }}
              </button>
            </div>
          </div>
        </div>

        <!-- Chat Settings -->
        <div class="settings-section">
          <h4>Chat</h4>
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Auto-scroll</span>
              <span class="setting-description">Automatically scroll to new messages</span>
            </div>
            <div class="setting-control">
              <label class="toggle">
                <input
                  type="checkbox"
                  :checked="uiStore.autoScroll"
                  @change="uiStore.setAutoScroll(!uiStore.autoScroll)"
                />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Show timestamps</span>
              <span class="setting-description">Display message timestamps</span>
            </div>
            <div class="setting-control">
              <label class="toggle">
                <input
                  type="checkbox"
                  :checked="uiStore.showTimestamps"
                  @change="uiStore.setShowTimestamps(!uiStore.showTimestamps)"
                />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>

        <!-- About -->
        <div class="settings-section">
          <h4>About</h4>
          <div class="about-info">
            <p><strong>HyperEternal Agent</strong></p>
            <p>Version 0.1.0</p>
            <p class="about-description">
              An autonomous AI-powered coding system that continuously develops
              and improves software projects.
            </p>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-primary" @click="close">Done</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()

const themes = [
  { id: 'dark' as const, name: 'Dark', icon: '🌙' },
  { id: 'light' as const, name: 'Light', icon: '☀️' },
]

function close() {
  uiStore.closeSettingsModal()
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

.modal-content {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 480px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  background: var(--bg-secondary);
  z-index: 1;
}

.modal-header h3 {
  font-size: 1.1rem;
}

.modal-body {
  padding: var(--spacing-lg);
}

.settings-section {
  margin-bottom: var(--spacing-lg);
}

.settings-section:last-child {
  margin-bottom: 0;
}

.settings-section h4 {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-md);
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) 0;
}

.setting-info {
  flex: 1;
}

.setting-label {
  display: block;
  font-weight: 500;
}

.setting-description {
  display: block;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.setting-control {
  flex-shrink: 0;
}

/* Theme buttons */
.theme-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--bg-tertiary);
  border: 2px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.theme-btn:first-child {
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}

.theme-btn:last-child {
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.theme-btn:hover {
  background: var(--bg-hover);
}

.theme-btn.active {
  background: var(--accent-primary);
  color: var(--bg-primary);
  border-color: var(--accent-primary);
}

/* Toggle switch */
.toggle {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: var(--bg-tertiary);
  border-radius: 26px;
  transition: var(--transition-fast);
}

.toggle-slider::before {
  position: absolute;
  content: '';
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background: var(--text-primary);
  border-radius: 50%;
  transition: var(--transition-fast);
}

.toggle input:checked + .toggle-slider {
  background: var(--accent-primary);
}

.toggle input:checked + .toggle-slider::before {
  transform: translateX(22px);
  background: var(--bg-primary);
}

/* About section */
.about-info {
  font-size: 0.9rem;
}

.about-info p {
  margin-bottom: var(--spacing-xs);
}

.about-description {
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-top: var(--spacing-sm);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}
</style>
