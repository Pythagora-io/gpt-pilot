{% raw %}
import { NavigationMenu } from "@/components/ui/navigation-menu"
import { ThemeToggle } from "@/components/themeToggle"

export function Header() {
  return (
    <header className="fixed top-0 w-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-50 border-b">
      <div className="container flex h-14 items-center">
        <NavigationMenu className="mx-6">
          <nav className="flex items-center space-x-6 text-sm font-medium">
            <a href="#" className="transition-colors hover:text-foreground/80">Home</a>
          </nav>
        </NavigationMenu>
        <div className="flex items-center ml-auto space-x-2">
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
{% endraw %}