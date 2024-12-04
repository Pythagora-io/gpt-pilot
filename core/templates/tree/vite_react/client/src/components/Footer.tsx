{% raw %}
import { Separator } from "@/components/ui/separator"

export function Footer() {
  return (
    <footer className="fixed bottom-0 w-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-t">
      <div className="container flex h-14 items-center justify-between">
        <p className="mx-6 text-sm text-muted-foreground">
          Built by Pythagora
        </p>
        <div className="flex items-center space-x-4">
          <a href="#" className="text-sm text-muted-foreground hover:text-foreground">
            Privacy
          </a>
          <Separator orientation="vertical" className="h-4" />
          <a href="#" className="text-sm text-muted-foreground hover:text-foreground">
            Terms
          </a>
        </div>
      </div>
    </footer>
  )
}
{% endraw %}