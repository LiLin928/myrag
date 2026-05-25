import { Modal, Table, Button, Tag, Space, message } from 'antd'
import { ClockCircleOutlined, RollbackOutlined } from '@ant-design/icons'
import { SkillVersion } from '../../types/models'

interface VersionHistoryProps {
  open: boolean
  versions: SkillVersion[]
  onClose: () => void
  onRollback: (versionNumber: number) => void
}

export function VersionHistory({ open, versions, onClose, onRollback }: VersionHistoryProps) {
  const handleRollback = (versionNumber: number) => {
    Modal.confirm({
      title: '确认回滚',
      content: `回滚到版本 ${versionNumber}? 当前文件将被替换。`,
      onOk: async () => {
        try {
          await onRollback(versionNumber)
          message.success(`已回滚到版本 ${versionNumber}`)
          onClose()
        } catch {
          message.error('回滚失败')
        }
      },
    })
  }

  const columns = [
    {
      title: '版本',
      dataIndex: 'version_number',
      key: 'version_number',
      render: (num: number) => <Tag color="blue">v{num}</Tag>,
    },
    {
      title: '变更摘要',
      dataIndex: 'change_summary',
      key: 'change_summary',
      ellipsis: true,
    },
    {
      title: '文件数',
      key: 'file_count',
      render: (record: SkillVersion) => record.files_manifest?.length || 0,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => (
        <Space>
          <ClockCircleOutlined />
          {new Date(time).toLocaleString()}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: SkillVersion) => (
        <Button
          size="small"
          icon={<RollbackOutlined />}
          onClick={() => handleRollback(record.version_number)}
        >
          回滚
        </Button>
      ),
    },
  ]

  return (
    <Modal
      title="版本历史"
      open={open}
      onCancel={onClose}
      footer={null}
      width={700}
    >
      <Table
        dataSource={versions}
        columns={columns}
        rowKey="id"
        pagination={false}
        size="small"
      />
    </Modal>
  )
}