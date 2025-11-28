"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { authApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FolderOpen,
  MessageSquare,
  FileSearch,
  Calculator,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Scale,
  Users,
  Bell,
  User as UserIcon,
  HelpCircle,
  Search as SearchIcon,
  MoreVertical,
  CreditCard,
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
import { useState, useEffect } from "react";

interface NavItem {
  titleKey: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

const mainNavItems: NavItem[] = [
  {
    titleKey: "nav.dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
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
  {
    titleKey: "nav.calculator",
    href: "/calculator",
    icon: Calculator,
  },
];

const secondaryNavItems: NavItem[] = [
  {
    titleKey: "nav.settings",
    href: "/settings",
    icon: Settings,
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
        setUserName(user.name || "User");
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
        "flex flex-col h-screen border-r bg-card transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className={cn(
        "flex items-center h-14 px-4 border-b",
        collapsed ? "justify-center" : "justify-between"
      )}>
        {collapsed ? (
          <button
            onClick={() => setCollapsed(false)}
            className="flex items-center gap-2"
            aria-label="Déployer le menu"
          >
            <Scale className="h-6 w-6 text-primary" />
          </button>
        ) : (
          <Link
            href="/dashboard"
            className="flex items-center gap-2"
          >
            <Scale className="h-6 w-6 text-primary" />
            <span className="font-semibold text-lg">{t("common.appName")}</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          className={cn("h-8 w-8", collapsed && "hidden")}
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
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
                collapsed && "justify-center px-2"
              )}
              title={collapsed ? title : undefined}
              onClick={(e) => handleNavClick(e, item.href)}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span>{title}</span>}
              {!collapsed && item.badge !== undefined && (
                <span className="ml-auto bg-primary/10 text-primary text-xs px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom Section */}
      <div className="px-2 py-2 border-t space-y-1">
        {/* Settings */}
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
            pathname === "/settings"
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground",
            collapsed && "justify-center px-2"
          )}
          title={collapsed ? "Settings" : undefined}
          onClick={(e) => handleNavClick(e, "/settings")}
        >
          <Settings className="h-5 w-5 shrink-0" />
          {!collapsed && <span>Settings</span>}
        </Link>

        {/* Get Help */}
        <button
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors w-full",
            "text-muted-foreground hover:bg-muted hover:text-foreground",
            collapsed && "justify-center px-2"
          )}
          title={collapsed ? "Get Help" : undefined}
          onClick={() => window.open("https://docs.example.com", "_blank")}
        >
          <HelpCircle className="h-5 w-5 shrink-0" />
          {!collapsed && <span>Get Help</span>}
        </button>

        {/* Search */}
        <button
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors w-full",
            "text-muted-foreground hover:bg-muted hover:text-foreground",
            collapsed && "justify-center px-2"
          )}
          title={collapsed ? "Search" : undefined}
          onClick={() => router.push("/dashboard")}
        >
          <SearchIcon className="h-5 w-5 shrink-0" />
          {!collapsed && <span>Search</span>}
        </button>

        {/* User Profile with Menu */}
        {!collapsed && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 px-3 py-2 hover:bg-muted rounded-md transition-colors w-full text-left">
                {/* Avatar */}
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-semibold shrink-0">
                  {getUserInitials(userName)}
                </div>

                {/* Name and Email */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{userName}</p>
                  <p className="text-xs text-muted-foreground truncate">{userEmail}</p>
                </div>

                {/* More Menu Icon */}
                <MoreVertical className="h-4 w-4 shrink-0 text-muted-foreground" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              {/* User Info Header */}
              <div className="flex items-center gap-2 px-2 py-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-semibold">
                  {getUserInitials(userName)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{userName}</p>
                  <p className="text-xs text-muted-foreground truncate">{userEmail}</p>
                </div>
              </div>
              <DropdownMenuSeparator />

              {/* Account */}
              <DropdownMenuItem onClick={() => router.push("/settings/account")}>
                <UserIcon className="h-4 w-4 mr-2" />
                Account
              </DropdownMenuItem>

              {/* Billing */}
              <DropdownMenuItem onClick={() => router.push("/settings/billing")}>
                <CreditCard className="h-4 w-4 mr-2" />
                Billing
              </DropdownMenuItem>

              {/* Notifications */}
              <DropdownMenuItem onClick={() => router.push("/settings/notifications")}>
                <Bell className="h-4 w-4 mr-2" />
                Notifications
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              {/* Log out */}
              <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                <LogOut className="h-4 w-4 mr-2" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Collapsed mode: Just show avatar with menu */}
        {collapsed && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="w-full flex justify-center px-2 py-2 hover:bg-muted rounded-md transition-colors">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-semibold">
                  {getUserInitials(userName)}
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              {/* Same menu as above */}
              <div className="flex items-center gap-2 px-2 py-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-semibold">
                  {getUserInitials(userName)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{userName}</p>
                  <p className="text-xs text-muted-foreground truncate">{userEmail}</p>
                </div>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/settings/account")}>
                <UserIcon className="h-4 w-4 mr-2" />
                Account
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push("/settings/billing")}>
                <CreditCard className="h-4 w-4 mr-2" />
                Billing
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push("/settings/notifications")}>
                <Bell className="h-4 w-4 mr-2" />
                Notifications
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                <LogOut className="h-4 w-4 mr-2" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {/* Expand Button (when collapsed) */}
      {collapsed && (
        <div className="p-2 border-t">
          <Button
            variant="ghost"
            size="icon"
            className="w-full h-8"
            onClick={() => setCollapsed(false)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </aside>
  );
}
