<template>
  <div class="login-page"
    v-bkloading="{ isLoading: loading, title: '登录中…', opacity: 1 }">
    <div class="login-card">
      <h1 class="login-title">bk-cmdb-lite</h1>
      <p class="login-sub">配置平台 · 登录</p>

      <form class="login-form" @submit.prevent="onSubmit">
        <label class="login-label">用户名</label>
        <input
          v-model.trim="form.bk_user_name"
          class="login-input"
          type="text"
          placeholder="请输入用户名"
          autocomplete="username"
          @keyup.enter="onSubmit" />

        <label class="login-label">密码</label>
        <input
          v-model.trim="form.bk_password"
          class="login-input"
          type="password"
          placeholder="请输入密码"
          autocomplete="current-password"
          @keyup.enter="onSubmit" />

        <div class="login-error" v-if="error">{{ error }}</div>

        <button class="login-btn" type="submit" :disabled="loading">
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>

      <p class="login-hint" v-if="skipLoginHint">
        当前为免登录模式，正在跳转…
      </p>
    </div>
  </div>
</template>

<script>
import { login as apiLogin } from '@/api/auth'
import { setToken, setUserName, getToken, getSkipLogin } from '@/auth'
import { MENU_INDEX } from '@/dictionary/menu-symbol'

export default {
  name: 'LoginView',
  data() {
    return {
      form: { bk_user_name: '', bk_password: '' },
      loading: false,
      error: '',
      skipLoginHint: false
    }
  },
  created() {
    // 已持 token 或处于免登录模式：直接进入应用
    if (getToken() || getSkipLogin()) {
      this.skipLoginHint = !!getSkipLogin() && !getToken()
      this.$router.replace(this.redirectTarget())
    }
  },
  methods: {
    redirectTarget() {
      const r = this.$route.query.redirect
      // 校验回跳参数：必须为非空、以 / 开头的站内路径，
      // 且不能是登录页本身（避免「登录 → 跳登录」死循环）。
      // 无参数或参数异常时，兜底回到首页（MENU_INDEX）。
      const isValidRedirect = typeof r === 'string'
        && r.length > 0
        && r.startsWith('/')
        && r !== '/login'
      return isValidRedirect ? { path: r } : { name: MENU_INDEX }
    },
    async onSubmit() {
      this.error = ''
      if (!this.form.bk_user_name || !this.form.bk_password) {
        this.error = '请输入用户名和密码'
        return
      }
      this.loading = true
      try {
        const data = await apiLogin(this.form)
        setToken(data.bk_token)
        setUserName(data.bk_user_name)
        this.$store.commit('user/setUser', { name: data.bk_user_name, skipLogin: false })
        this.$router.replace(this.redirectTarget())
      } catch (e) {
        // 业务层（1302101 用户名或密码错误等）与系统层（网络 / 5xx / 网关）错误
        // 统一走项目公共错误提示（$handleApiError → bk-message / 无权限弹窗），
        // 不再用本地文本静默吞掉。
        this.$handleApiError(e)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f4f5f8;
}
.login-card {
  width: 360px;
  background: #fff;
  border-radius: 4px;
  padding: 36px 32px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, .1);
}
.login-title {
  font-size: 22px;
  margin: 0 0 4px;
  color: #313238;
}
.login-sub {
  margin: 0 0 28px;
  color: #979ba5;
  font-size: 13px;
}
.login-form {
  display: flex;
  flex-direction: column;
}
.login-label {
  font-size: 13px;
  color: #63656e;
  margin-bottom: 6px;
}
.login-input {
  height: 38px;
  padding: 0 12px;
  border: 1px solid #c4c6cc;
  border-radius: 2px;
  font-size: 14px;
  outline: none;
  margin-bottom: 18px;
}
.login-input:focus {
  border-color: #3a84ff;
}
.login-error {
  color: #ff4d4f;
  font-size: 12px;
  margin-bottom: 12px;
}
.login-btn {
  height: 40px;
  border: none;
  border-radius: 2px;
  background: #3a84ff;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.login-btn:disabled {
  opacity: .6;
  cursor: not-allowed;
}
.login-hint {
  margin: 16px 0 0;
  text-align: center;
  color: #979ba5;
  font-size: 12px;
}
</style>
