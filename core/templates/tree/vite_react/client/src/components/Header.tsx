{% raw %}
import { Bell{% endraw %}{% if options.auth %}, LogOut{% endif %}{% raw %} } from "lucide-react"
import { Button } from "./ui/button"
import { ThemeToggle } from "./ui/theme-toggle"
import { useAuth } from "@/contexts/AuthContext"
import { useNavigate } from "react-router-dom"

export function Header() {
{% endraw %}
{% if options.auth %}
  const { logout } = useAuth()
{% endif %}
  const navigate = useNavigate()
{% if options.auth %}
  const handleLogout = () => {
    logout()
    navigate("/login")
  }
{% endif %}
  return (
    <header className="fixed top-0 z-50 w-full border-b bg-background/80 backdrop-blur-sm">
      <div className="flex h-16 items-center justify-between px-6">
        <div className="text-xl font-bold">Home</div>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          {% if options.auth %}
          <Button variant="ghost" size="icon" onClick={handleLogout}>
            <LogOut className="h-5 w-5" />
          </Button>
          {% endif %}
        </div>
      </div>
    </header>
  )
}
