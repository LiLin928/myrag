import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/Layout/AppLayout'
import { Login } from './pages/Login'
import { useAuthStore } from './stores/authStore'
import { KnowledgeList } from './pages/Knowledge/List'
import { KnowledgeDetail } from './pages/Knowledge/Detail'
import { DocumentList } from './pages/Documents/List'
import { DocumentUpload } from './pages/Documents/Upload'
import { DocumentDetail } from './pages/Documents/Detail'
import { SkillList } from './pages/Skills/List'
import { SkillEditor } from './pages/Skills/Editor'
import { SkillGenerate } from './pages/Skills/Generate'
import { ChatList } from './pages/Chat/List'
import { ConversationView } from './pages/Chat/Conversation'
import { WorkflowList } from './pages/Workflows/List'
import { WorkflowEditor } from './pages/Workflows/Editor'
import { WorkflowExecute } from './pages/Workflows/Execute'
import { WorkflowHistory } from './pages/Workflows/History'
import { WorkflowTemplates } from './pages/Workflows/Templates'
import { AgentEditor } from './pages/Agents/Editor'
import { UserList } from './pages/Users/List'
import { SearchPage } from './pages/Search/Search'
import { ToolList } from './pages/Tools/List'
import { ModelList } from './pages/Settings/ModelList'
import { SystemPromptList } from './pages/SystemPrompts/List'
import { DocumentChunksPage } from './pages/Knowledge/DocumentChunksPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function KnowledgeRoutes() {
  return (
    <Routes>
      <Route index element={<KnowledgeList />} />
      <Route path=":id" element={<KnowledgeDetail />} />
      <Route path=":knowledgeId/documents/:documentId/chunks" element={<DocumentChunksPage />} />
    </Routes>
  )
}

function DocumentRoutes() {
  return (
    <Routes>
      <Route index element={<DocumentList />} />
      <Route path="upload" element={<DocumentUpload />} />
      <Route path=":id" element={<DocumentDetail />} />
    </Routes>
  )
}

function SkillRoutes() {
  return (
    <Routes>
      <Route index element={<SkillList />} />
      <Route path="new" element={<SkillEditor />} />
      <Route path="generate" element={<SkillGenerate />} />
      <Route path=":id" element={<SkillEditor />} />
    </Routes>
  )
}

function WorkflowRoutes() {
  return (
    <Routes>
      <Route index element={<WorkflowList />} />
      <Route path="history" element={<WorkflowHistory />} />
      <Route path="templates" element={<WorkflowTemplates />} />
      <Route path="new" element={<WorkflowEditor />} />
      <Route path=":id" element={<WorkflowEditor />} />
      <Route path=":id/execute" element={<WorkflowExecute />} />
    </Routes>
  )
}

function ChatRoutes() {
  return (
    <Routes>
      <Route index element={<ChatList />} />
      <Route path=":id" element={<ConversationView />} />
    </Routes>
  )
}

function AgentRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="new" />} />
      <Route path="new" element={<AgentEditor />} />
      <Route path=":id" element={<AgentEditor />} />
    </Routes>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={<PrivateRoute><AppLayout /></PrivateRoute>}
      >
        <Route index element={<Navigate to="/search" />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="knowledge/*" element={<KnowledgeRoutes />} />
        <Route path="documents/*" element={<DocumentRoutes />} />
        <Route path="skills/*" element={<SkillRoutes />} />
        <Route path="agents/*" element={<AgentRoutes />} />
        <Route path="workflows/*" element={<WorkflowRoutes />} />
        <Route path="chat/*" element={<ChatRoutes />} />
        <Route path="users" element={<UserList />} />
        <Route path="tools" element={<ToolList />} />
        <Route path="system-prompts" element={<SystemPromptList />} />
        <Route path="settings" element={<ModelList />} />
      </Route>
    </Routes>
  )
}

export default App