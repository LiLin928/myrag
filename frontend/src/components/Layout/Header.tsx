import { Layout, Avatar, Dropdown, Space } from 'antd'
import { UserOutlined, LogoutOutlined } from '@ant-design/icons'
import { useAuthStore } from '../../stores/authStore'
import { useNavigate } from 'react-router-dom'

export function Header() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const menuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        logout()
        navigate('/login')
      },
    },
  ]

  return (
    <Layout.Header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      background: '#fff',
      boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
    }}>
      <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#1890ff' }}>
        MyRAG
      </div>
      <Dropdown menu={{ items: menuItems }} placement="bottomRight">
        <Space style={{ cursor: 'pointer' }}>
          <Avatar icon={<UserOutlined />} style={{ background: '#1890ff' }} />
          <span>{user?.username || '用户'}</span>
        </Space>
      </Dropdown>
    </Layout.Header>
  )
}