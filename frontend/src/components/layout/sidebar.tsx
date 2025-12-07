"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { authApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  FolderOpen,
  MessageSquare,
  FileSearch,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Scale,
  HelpCircle,
  MoreVertical,
  User,
  CreditCard,
  Bell,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useState, useEffect } from "react";
import { ModelSelector } from "./model-selector";

interface NavItem {
  titleKey: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

const mainNavItems: NavItem[] = [
  {
    titleKey: "nav.cases",
    href: "/cases",
    icon: FolderOpen,
  },
  {
    titleKey: "nav.assistant",
    href: "/assistant",
    icon: MessageSquare,
  },
  {
    titleKey: "nav.analysis",
    href: "/analysis",
    icon: FileSearch,
  },
];


export function Sidebar() {
  const t = useTranslations();
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [userName, setUserName] = useState("User");
  const [userEmail, setUserEmail] = useState("user@example.com");

  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const user = await authApi.getCurrentUser();
        setIsAdmin(user.role === "admin");
        setUserName(`${user.prenom} ${user.nom}`.trim() || "User");
        setUserEmail(user.email || "user@example.com");
      } catch {
        setIsAdmin(false);
      }
    };
    if (authApi.isAuthenticated()) {
      fetchUserInfo();
    }
  }, []);

  const handleLogout = () => {
    authApi.logout();
    router.push("/login");
  };

  const handleNavClick = (e: React.MouseEvent, href: string) => {
    // If sidebar is collapsed and we're already on this page, just expand
    if (collapsed && (pathname === href || pathname.startsWith(href + "/"))) {
      e.preventDefault();
      setCollapsed(false);
    }
    // Otherwise, let the link navigate normally
  };

  // Get user initials for avatar
  const getUserInitials = (name: string): string => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <aside
      className={cn(
        "flex flex-col h-screen bg-sidebar text-sidebar-foreground transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className={cn(
        "flex items-center px-4 py-4",
        collapsed ? "justify-center" : "justify-between"
      )}>
        {collapsed ? (
          <button
            onClick={() => setCollapsed(false)}
            className="flex items-center gap-2"
            aria-label="Déployer le menu"
          >
            <Scale className="h-6 w-6 text-sidebar-foreground" />
          </button>
        ) : (
          <Link
            href="/cases"
            className="flex items-center gap-2"
          >
            <Scale className="h-6 w-6 text-sidebar-foreground" />
            <span className="font-semibold text-lg text-sidebar-foreground">{t("common.appName")}</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          className={cn("h-8 w-8 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground", collapsed && "hidden")}
          onClick={() => setCollapsed(!collapsed)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-2 py-2 space-y-1 overflow-y-auto">
        {mainNavItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          const title = t(item.titleKey);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-2 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                collapsed && "justify-center px-2"
              )}
              title={collapsed ? title : undefined}
              onClick={(e) => handleNavClick(e, item.href)}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span>{title}</span>}
              {!collapsed && item.badge !== undefined && (
                <span className="ml-auto bg-sidebar-accent text-sidebar-foreground text-xs px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom Section - Model Selector + User Profile with Menu */}
      <div>
        {/* Model Selector */}
        <ModelSelector collapsed={collapsed} />

        {/* User Profile with Menu */}
        <div className="px-2 py-2">
        {/* User Profile with Menu - Expanded mode */}
        {!collapsed && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-3 px-2 py-2 hover:bg-sidebar-accent rounded-md transition-colors w-full text-left">
                <Avatar className="h-8 w-8">
                  <AvatarImage src="" alt={userName} />
                  <AvatarFallback className="bg-sidebar-foreground text-sidebar text-xs font-medium">
                    {getUserInitials(userName)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate text-sidebar-foreground">{userName}</p>
                  <p className="text-xs text-sidebar-foreground/60 truncate">{userEmail}</p>
                </div>
                <MoreVertical className="h-4 w-4 shrink-0 text-sidebar-foreground/60" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" side="top" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{userName}</p>
                  <p className="text-xs leading-none text-muted-foreground">{userEmail}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/settings")}>
                <User className="mr-2 h-4 w-4" />
                <span>Account</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push("/settings")}>
                <Settings className="mr-2 h-4 w-4" />
                <span>Settings</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => window.open("https://docs.example.com", "_blank")}>
                <HelpCircle className="mr-2 h-4 w-4" />
                <span>Get Help</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Collapsed mode: Just show avatar with menu */}
        {collapsed && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="w-full flex justify-center px-2 py-2 hover:bg-sidebar-accent rounded-md transition-colors">
                <Avatar className="h-8 w-8">
                  <AvatarImage src="" alt={userName} />
                  <AvatarFallback className="bg-sidebar-foreground text-sidebar text-xs font-medium">
                    {getUserInitials(userName)}
                  </AvatarFallback>
                </Avatar>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" side="right" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{userName}</p>
                  <p className="text-xs leading-none text-muted-foreground">{userEmail}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/settings")}>
                <User className="mr-2 h-4 w-4" />
                <span>Account</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push("/settings")}>
                <Settings className="mr-2 h-4 w-4" />
                <span>Settings</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => window.open("https://docs.example.com", "_blank")}>
                <HelpCircle className="mr-2 h-4 w-4" />
                <span>Get Help</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
        </div>
      </div>

      {/* Expand Button (when collapsed) */}
      {collapsed && (
        <div className="p-2 border-t border-sidebar-border">
          <Button
            variant="ghost"
            size="icon"
            className="w-full h-8 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
            onClick={() => setCollapsed(false)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </aside>
  );
}
