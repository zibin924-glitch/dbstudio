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
        <el-input v-model="formData.database_name" placeholder="Database name" />
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

      <el-form-item label="Extra Params">
        <el-input
          v-model="formData.extra_params"
          type="textarea"
          :rows="3"
          placeholder='Optional JSON, e.g. {"charset": "utf8mb4"}'
        />
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
  extra_params: ''
})

const formData = reactive(getDefaultForm())

const isEdit = ref(false)

const formRules = {
  name: [{ required: true, message: 'Please enter connection name', trigger: 'blur' }],
  db_type: [{ required: true, message: 'Please select database type', trigger: 'change' }],
  host: [{ required: true, message: 'Please enter host', trigger: 'blur' }],
  port: [{ required: true, message: 'Please enter port', trigger: 'blur' }],
  username: [{ required: true, message: 'Please enter username', trigger: 'blur' }]
}

watch(() => props.visible, (val) => {
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
</style>
