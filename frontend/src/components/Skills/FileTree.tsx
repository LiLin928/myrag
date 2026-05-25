import { Tree, Button, Space, Modal, Input, message } from 'antd'
import {
  PlusOutlined,
  UploadOutlined,
  DeleteOutlined,
  FileOutlined,
  FolderOutlined,
} from '@ant-design/icons'
import { useState, useMemo } from 'react'
import type { TreeDataNode, TreeProps } from 'antd'
import { SkillFile } from '../../types/models'

interface FileTreeProps {
  files: SkillFile[]
  selectedPath: string | null
  onSelect: (path: string) => void
  onCreateFile: (path: string, content: string) => void
  onDeleteFile: (path: string) => void
  onUploadFiles: (files: File[]) => void
}

export function FileTree({
  files,
  selectedPath,
  onSelect,
  onCreateFile,
  onDeleteFile,
  onUploadFiles,
}: FileTreeProps) {
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [newFileName, setNewFileName] = useState('')

  const treeData = useMemo(() => {
    const buildTree = (fileList: SkillFile[]): TreeDataNode[] => {
      const root: Record<string, TreeDataNode> = {}

      fileList.forEach((file) => {
        const parts = file.file_path.split('/')
        let current = root

        parts.forEach((part, index) => {
          const isFile = index === parts.length - 1
          const key = parts.slice(0, index + 1).join('/')

          if (!current[key]) {
            current[key] = {
              key,
              title: isFile ? (
                <Space>
                  <FileOutlined />
                  {part}
                  {file.is_entry && <span style={{ color: '#52c41a', fontSize: 10 }}>入口</span>}
                </Space>
              ) : (
                <Space>
                  <FolderOutlined />
                  {part}
                </Space>
              ),
              isLeaf: isFile,
              children: isFile ? undefined : [],
            }
          }

          if (!isFile && current[key].children) {
            current = current[key].children!.reduce((acc, child) => {
              acc[child.key as string] = child
              return acc
            }, {} as Record<string, TreeDataNode>)
          }
        })
      })

      return Object.values(root).sort((a, b) => {
        if (a.isLeaf !== b.isLeaf) return a.isLeaf ? 1 : -1
        return (a.key as string).localeCompare(b.key as string)
      })
    }

    return buildTree(files)
  }, [files])

  const handleSelect: TreeProps['onSelect'] = (selectedKeys) => {
    if (selectedKeys.length > 0) {
      const key = selectedKeys[0] as string
      const allNodes = [...treeData, ...treeData.flatMap((n) => n.children || [])]
      const node = allNodes.find((n) => n.key === key)
      if (node?.isLeaf) {
        onSelect(key)
      }
    }
  }

  const handleCreateFile = () => {
    if (!newFileName) {
      message.error('请输入文件名')
      return
    }
    onCreateFile(newFileName, '')
    setCreateModalOpen(false)
    setNewFileName('')
  }

  const handleUpload = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = true
    input.onchange = (e) => {
      const fileList = (e.target as HTMLInputElement).files
      if (fileList && fileList.length > 0) {
        onUploadFiles(Array.from(fileList))
      }
    }
    input.click()
  }

  const handleDelete = () => {
    if (!selectedPath) return
    Modal.confirm({
      title: '确认删除',
      content: `删除文件 ${selectedPath}?`,
      onOk: () => onDeleteFile(selectedPath),
    })
  }

  return (
    <div style={{ padding: '8px' }}>
      <Space style={{ marginBottom: 8, width: '100%', justifyContent: 'space-between' }}>
        <Button size="small" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
          新建
        </Button>
        <Button size="small" icon={<UploadOutlined />} onClick={handleUpload}>
          上传
        </Button>
        <Button
          size="small"
          icon={<DeleteOutlined />}
          danger
          disabled={!selectedPath}
          onClick={handleDelete}
        >
          删除
        </Button>
      </Space>

      <Tree
        treeData={treeData}
        selectedKeys={selectedPath ? [selectedPath] : []}
        onSelect={handleSelect}
        showLine
        defaultExpandAll
      />

      <Modal
        title="新建文件"
        open={createModalOpen}
        onOk={handleCreateFile}
        onCancel={() => setCreateModalOpen(false)}
      >
        <Input
          placeholder="文件名（如 main.py, scripts/helper.sh）"
          value={newFileName}
          onChange={(e) => setNewFileName(e.target.value)}
        />
      </Modal>
    </div>
  )
}