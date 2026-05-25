import { Menu } from 'antd'
import {
  DatabaseOutlined,
  FileTextOutlined,
  CodeOutlined,
  ApartmentOutlined,
  MessageOutlined,
  TeamOutlined,
  SearchOutlined,
  SettingOutlined,
  ApiOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const menuItems = [
  { key: '/search', icon: <SearchOutlined />, label: '搜索' },
  { key: '/knowledge', icon: <DatabaseOutlined />, label: '知识库' },
  { key: '/documents', icon: <FileTextOutlined />, label: '文档' },
  { key: '/skills', icon: <CodeOutlined />, label: '技能' },
  { key: '/tools', icon: <ApiOutlined />, label: '工具' },
  { key: '/workflows', icon: <ApartmentOutlined />, label: '工作流' },
  { key: '/chat', icon: <MessageOutlined />, label: '对话' },
  { key: '/users', icon: <TeamOutlined />, label: '用户' },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
]

export function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  const selectedKey = menuItems.find(item => location.pathname.startsWith(item.key))?.key || '/search'

  return (
    <Menu
      mode="inline"
      selectedKeys={[selectedKey]}
      items={menuItems}
      onClick={({ key }) => navigate(key)}
      style={{ height: '100%', borderRight: 0 }}
    />
  )
}