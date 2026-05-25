import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Card, Input, Switch, Button, Space, message, Spin, Modal, Alert } from 'antd'
import { SaveOutlined, HistoryOutlined, SettingOutlined } from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { useSkillStore } from '../../stores/skillStore'
import { FileTree } from '../../components/Skills/FileTree'
import { VersionHistory } from '../../components/Skills/VersionHistory'

const LANGUAGE_MAP: Record<string, string> = {
  python: 'python',
  shell: 'shell',
  markdown: 'markdown',
  yaml: 'yaml',
  json: 'json',
  text: 'plaintext',
  unknown: 'plaintext',
}

export function SkillEditor() {
  const { id } = useParams()
  const {
    currentSkill,
    currentFiles,
    currentVersions,
    selectedFilePath,
    fileContent,
    loading,
    saving,
    fetchOne,
    fetchFiles,
    fetchFileContent,
    fetchVersions,
    update,
    createFile,
    updateFile,
    deleteFile,
    uploadFiles,
    selectFile,
    rollback,
  } = useSkillStore()

  const [editedContent, setEditedContent] = useState('')
  const [versionModalOpen, setVersionModalOpen] = useState(false)
  const [settingsModalOpen, setSettingsModalOpen] = useState(false)
  const [displayName, setDisplayName] = useState('')
  const [isPublic, setIsPublic] = useState(false)
  const [entryCommand, setEntryCommand] = useState('')

  const isNew = id === 'new'

  useEffect(() => {
    if (!isNew && id) {
      fetchOne(id)
      fetchFiles(id)
      fetchVersions(id)
    }
  }, [id])

  useEffect(() => {
    if (currentFiles.length > 0 && !selectedFilePath) {
      const entryFile = currentFiles.find((f) => f.is_entry)
      const firstFile = entryFile || currentFiles[0]
      if (firstFile && id) {
        fetchFileContent(id, firstFile.file_path)
      }
    }
  }, [currentFiles, selectedFilePath])

  useEffect(() => {
    if (fileContent) {
      setEditedContent(fileContent)
    }
  }, [fileContent])

  useEffect(() => {
    if (currentSkill) {
      setDisplayName(currentSkill.display_name || '')
      setIsPublic(currentSkill.is_public || false)
      setEntryCommand(currentSkill.entry_command || 'python main.py')
    }
  }, [currentSkill])

  const saveContent = useCallback(async () => {
    if (!id || !selectedFilePath || editedContent === fileContent) return

    try {
      await updateFile(id, selectedFilePath, editedContent)
      message.success('已保存')
    } catch {
      message.error('保存失败')
    }
  }, [id, selectedFilePath, editedContent, fileContent])

  useEffect(() => {
    const timer = setTimeout(saveContent, 500)
    return () => clearTimeout(timer)
  }, [editedContent])

  const handleSelectFile = (path: string) => {
    selectFile(path)
    if (id) {
      fetchFileContent(id, path)
    }
  }

  const handleCreateFile = async (path: string, content: string) => {
    try {
      await createFile(id!, { file_path: path, content })
      message.success(`创建文件 ${path}`)
      handleSelectFile(path)
    } catch {
      message.error('创建失败')
    }
  }

  const handleDeleteFile = async (path: string) => {
    try {
      await deleteFile(id!, path)
      message.success(`删除文件 ${path}`)
    } catch {
      message.error('删除失败')
    }
  }

  const handleUploadFiles = async (files: File[]) => {
    try {
      await uploadFiles(id!, files)
      message.success(`上传 ${files.length} 个文件`)
    } catch {
      message.error('上传失败')
    }
  }

  const handleSaveSettings = async () => {
    try {
      await update(id!, {
        display_name: displayName,
        is_public: isPublic,
        entry_command: entryCommand,
      })
      message.success('设置已保存')
      setSettingsModalOpen(false)
    } catch {
      message.error('保存失败')
    }
  }

  const handleRollback = async (versionNumber: number) => {
    await rollback(id!, versionNumber)
  }

  const getLanguage = () => {
    if (!selectedFilePath) return 'plaintext'
    const file = currentFiles.find((f) => f.file_path === selectedFilePath)
    return LANGUAGE_MAP[file?.file_type || 'unknown']
  }

  if (!isNew && loading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 100px)' }}>
      <Card
        title="文件"
        style={{ width: 280, overflow: 'auto' }}
        extra={
          <Button
            icon={<HistoryOutlined />}
            size="small"
            onClick={() => setVersionModalOpen(true)}
          >
            版本
          </Button>
        }
      >
        {!isNew && currentFiles.length === 0 && (
          <Alert type="info" message="暂无文件，请新建或上传" style={{ marginBottom: 8 }} />
        )}
        {isNew ? (
          <Alert type="warning" message="请先保存技能后再添加文件" />
        ) : (
          <FileTree
            files={currentFiles}
            selectedPath={selectedFilePath}
            onSelect={handleSelectFile}
            onCreateFile={handleCreateFile}
            onDeleteFile={handleDeleteFile}
            onUploadFiles={handleUploadFiles}
          />
        )}
      </Card>

      <Card
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        title={
          <Space>
            <span>{currentSkill?.display_name || currentSkill?.internal_name || '新技能'}</span>
            <Switch
              checked={isPublic}
              onChange={setIsPublic}
              checkedChildren="公开"
              unCheckedChildren="私有"
              disabled={isNew}
            />
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<SettingOutlined />}
              onClick={() => setSettingsModalOpen(true)}
              disabled={isNew}
            >
              设置
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={saveContent}
              disabled={!selectedFilePath}
            >
              保存
            </Button>
          </Space>
        }
      >
        {!selectedFilePath ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
            选择左侧文件开始编辑
          </div>
        ) : (
          <Editor
            height="100%"
            language={getLanguage()}
            value={editedContent}
            onChange={(value) => setEditedContent(value || '')}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        )}
      </Card>

      <VersionHistory
        open={versionModalOpen}
        versions={currentVersions}
        onClose={() => setVersionModalOpen(false)}
        onRollback={handleRollback}
      />

      <Modal
        title="技能设置"
        open={settingsModalOpen}
        onOk={handleSaveSettings}
        onCancel={() => setSettingsModalOpen(false)}
      >
        <div style={{ marginBottom: 16 }}>
          <label>显示名称</label>
          <Input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="可修改的显示名称"
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label>执行命令</label>
          <Input
            value={entryCommand}
            onChange={(e) => setEntryCommand(e.target.value)}
            placeholder="如 python main.py --input {{input.data}}"
          />
        </div>
        <div>
          <label>公开状态</label>
          <Switch
            checked={isPublic}
            onChange={setIsPublic}
            checkedChildren="公开（所有用户可见）"
            unCheckedChildren="私有（仅自己可见）"
          />
        </div>
      </Modal>
    </div>
  )
}