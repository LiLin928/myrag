import { Layout } from 'antd'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function AppLayout() {
  return (
    <Layout style={{ height: '100vh' }}>
      <Layout.Sider width={200} style={{ background: '#fff' }}>
        <Sidebar />
      </Layout.Sider>
      <Layout>
        <Header />
        <Layout.Content style={{
          margin: '24px',
          padding: '24px',
          background: '#fff',
          borderRadius: '8px',
          overflow: 'auto',
        }}>
          <Outlet />
        </Layout.Content>
      </Layout>
    </Layout>
  )
}