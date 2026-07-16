<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="isEdit ? 'Edit Connection' : 'New Connection'"
    width="620px"
    destroy-on-close
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="120px"
      label-position="right"
    >
      <el-form-item label="Name" prop="name">
        <el-input v-model="formData.name" placeholder="Connection name" />
      </el-form-item>

      <el-form-item label="Database Type" prop="db_type">
        <el-select v-model="formData.db_type" placeholder="Select type" @change="onDbTypeChange" style="width: 100%;">
          <el-option label="MySQL" value="mysql" />
          <el-option label="PostgreSQL" value="postgresql" />
          <el-option label="Oracle" value="oracle" />
        </el-select>
      </el-form-item>

      <el-row :gutter="16">
        <el-col :span="16">
          <el-form-item label="Host" prop="host">
            <el-input v-model="formData.host" placeholder="localhost" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="Port" prop="port">
            <el-input-number v-model="formData.port" :min="1" :max="65535" controls-position="right" style="width: 100%;" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="Username" prop="username">
            <el-input v-model="formData.username" placeholder="Username" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="Password" prop="password">
            <el-input v-model="formData.password" type="password" show-password placeholder="Password" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="Database" prop="database_name">
        <el-input v-model="formData.database_name" placeholder="Database name" @blur="onDatabaseNameBlur" />
        <!-- H-F6: database_name 为空的非阻断性警告 -->
        <div v-if="databaseNameWarning" class="field-warning">
          <el-icon><Warning /></el-icon>
          <span>{{ databaseNameWarning }}</span>
        </div>
      </el-form-item>

      <el-form-item label="Group">
        <el-input v-model="formData.group_name" placeholder="Group name (optional)" />
      </el-form-item>

      <el-form-item label="Tags">
        <el-select
          v-model="formData.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="Add tags"
          style="width: 100%;"
        >
          <el-option v-for="tag in commonTags" :key="tag" :label="tag" :value="tag" />
        </el-select>
      </el-form-item>

      <el-divider content-position="left">Advanced Settings</el-divider>

      <el-form-item label="连接池大小">
        <el-input-number
          v-model="formData.pool_size"
          :min="1"
          :max="50"
          controls-position="right"
          style="width: 200px;"
        />
      </el-form-item>

      <el-form-item label="Extra Params" :error="extraParamsError">
        <el-input
          v-model="formData.extra_params"
          type="textarea"
          :rows="3"
          placeholder='Optional JSON, e.g. {"charset": "utf8mb4"}'
          :class="{ 'extra-params-error': extraParamsError }"
          @blur="validateExtraParams"
        />
        <!-- H-F6: JSON 格式错误时的内联提示 -->
        <div v-if="extraParamsError" class="field-error">
          {{ extraParamsError }}
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleTestConnection" :loading="testing" type="info" plain>
          <el-icon><Connection /></el-icon>
          Test Connection
        </el-button>
        <el-button @click="$emit('update:visible', false)">Cancel</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          {{ isEdit ? 'Update' : 'Save' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Warning } from '@element-plus/icons-vue'
import { useConnectionStore } from '@/stores/connection.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  connection: { type: Object, default: null }
})

const emit = defineEmits(['update:visible', 'saved'])

const connectionStore = useConnectionStore()
const formRef = ref(null)
const testing = ref(false)
const saving = ref(false)

// H-F6: extra_params JSON 校验错误信息
const extraParamsError = ref('')
// H-F6: database_name 为空时的警告提示
const databaseNameWarning = ref('')

// H-F6: 验证 extra_params 是否为合法 JSON
function validateExtraParams() {
  extraParamsError.value = ''
  const val = formData.extra_params
  if (!val || !val.trim()) return
  try {
    JSON.parse(val)
  } catch {
    extraParamsError.value = '请输入有效的 JSON 格式'
  }
}

// H-F6: database_name 为空时给出非阻断性警告
function onDatabaseNameBlur() {
  databaseNameWarning.value = formData.database_name ? '' : '建议填写数据库名称，留空将连接默认数据库'
}

const commonTags = ['production', 'staging', 'development', 'readonly', 'backup']

const defaultPorts = {
  mysql: 3306,
  postgresql: 5432,
  oracle: 1521
}

const getDefaultForm = () => ({
  name: '',
  db_type: 'mysql',
  host: 'localhost',
  port: 3306,
  username: '',
  password: '',
  database_name: '',
  group_name: '',
  tags: [],
  pool_size: 5,
  extra_params: ''
})

const formData = reactive(getDefaultForm())

const isEdit = ref(false)

// H-F6: 主机名/IP 地址验证规则
const HOST_REGEX = /^(localhost|(\d{1,3}\.){3}\d{1,3}|[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*)$/

function validateHost(rule, value, callback) {
  if (!value || !value.trim()) {
    callback(new Error('请输入主机地址'))
    return
  }
  if (!HOST_REGEX.test(value.trim())) {
    callback(new Error('请输入有效的 IP 地址或主机名'))
    return
  }
  // 额外校验 IPv4 每段不超过 255
  if (/^\d/.test(value) && value.includes('.')) {
    const parts = value.split('.')
    if (parts.length === 4 && parts.every(p => /^\d{1,3}$/.test(p))) {
      const invalid = parts.some(p => Number(p) > 255)
      if (invalid) {
        callback(new Error('请输入有效的 IP 地址或主机名'))
        return
      }
    }
  }
  callback()
}

const formRules = {
  name: [{ required: true, message: 'Please enter connection name', trigger: 'blur' }],
  db_type: [{ required: true, message: 'Please select database type', trigger: 'change' }],
  host: [
    { required: true, message: '请输入主机地址', trigger: 'blur' },
    { validator: validateHost, trigger: 'blur' }
  ],
  port: [{ required: true, message: 'Please enter port', trigger: 'blur' }],
  username: [{ required: true, message: 'Please enter username', trigger: 'blur' }]
}

watch(() => props.visible, (val) => {
  // H-F6: 打开弹窗时清除校验错误状态
  if (val) {
    extraParamsError.value = ''
    databaseNameWarning.value = ''
  }
  if (val && props.connection) {
    isEdit.value = true
    Object.assign(formData, {
      ...getDefaultForm(),
      ...props.connection,
      tags: props.connection.tags || []
    })
  } else if (val) {
    isEdit.value = false
    Object.assign(formData, getDefaultForm())
  }
})

function onDbTypeChange(type) {
  formData.port = defaultPorts[type] || 3306
}

async function handleTestConnection() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  testing.value = true
  try {
    const result = await connectionStore.testConnection({ ...formData })
    const data = result.data || result
    if (data.success || data.status === 'ok') {
      ElMessage.success('Connection successful!')
    } else {
      ElMessage.error(data.message || 'Connection failed')
    }
  } catch (error) {
    ElMessage.error('Connection test failed')
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  // H-F6: 保存前校验 extra_params JSON 格式
  if (formData.extra_params && formData.extra_params.trim()) {
    try {
      JSON.parse(formData.extra_params)
    } catch {
      extraParamsError.value = '请输入有效的 JSON 格式'
      return
    }
  }

  saving.value = true
  try {
    const payload = { ...formData }
    if (isEdit.value && props.connection) {
      await connectionStore.updateConnection(props.connection.id, payload)
      ElMessage.success('Connection updated')
    } else {
      await connectionStore.createConnection(payload)
      ElMessage.success('Connection created')
    }
    emit('update:visible', false)
    emit('saved')
  } catch (error) {
    ElMessage.error('Failed to save connection')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* H-F6: extra_params JSON 校验错误红框 */
.extra-params-error :deep(.el-textarea__inner) {
  border-color: #f56c6c !important;
}

/* H-F6: 字段级错误提示文字 */
.field-error {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 4px;
  line-height: 1.4;
}

/* H-F6: 字段级警告提示 */
.field-warning {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #e6a23c;
  font-size: 12px;
  margin-top: 4px;
  line-height: 1.4;
}
</style>
