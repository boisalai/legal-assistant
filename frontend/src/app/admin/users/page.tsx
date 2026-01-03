"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Pencil,
  Trash2,
  Search,
  UserPlus,
  Shield,
  ShieldCheck,
  Users,
  AlertCircle,
  Check,
  X,
  Eye,
  EyeOff,
  Loader2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { adminApi, authApi, AdminUser } from "@/lib/api";
import { AppShell } from "@/components/layout/app-shell";

export default function AdminUsersPage() {
  const t = useTranslations("admin");
  const router = useRouter();

  // State
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentUser, setCurrentUser] = useState<{ id: string; role: string } | null>(null);

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);

  // Form states
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formPassword, setFormPassword] = useState("");
  const [formRole, setFormRole] = useState("notaire");
  const [formActif, setFormActif] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Check if user is admin
  useEffect(() => {
    const checkAuth = async () => {
      if (!authApi.isAuthenticated()) {
        router.push("/login");
        return;
      }

      try {
        const user = await authApi.getCurrentUser();
        if (user.role !== "admin") {
          router.push("/dashboard");
          return;
        }
        setCurrentUser({ id: user.id, role: user.role });
      } catch {
        router.push("/login");
      }
    };

    checkAuth();
  }, [router]);

  // Load users
  const loadUsers = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await adminApi.listUsers();
      setUsers(response.users);
      setTotal(response.total);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur lors du chargement";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentUser) {
      loadUsers();
    }
  }, [currentUser]);

  // Filter users by search term
  const filteredUsers = users.filter(
    (user) =>
      user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Reset form
  const resetForm = () => {
    setFormName("");
    setFormEmail("");
    setFormPassword("");
    setFormRole("notaire");
    setFormActif(true);
    setShowPassword(false);
    setFormError(null);
  };

  // Open create dialog
  const openCreateDialog = () => {
    resetForm();
    setCreateDialogOpen(true);
  };

  // Open edit dialog
  const openEditDialog = (user: AdminUser) => {
    setSelectedUser(user);
    setFormName(user.name);
    setFormEmail(user.email);
    setFormPassword("");
    setFormRole(user.role);
    setFormActif(user.actif);
    setFormError(null);
    setEditDialogOpen(true);
  };

  // Open delete dialog
  const openDeleteDialog = (user: AdminUser) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
  };

  // Create user
  const handleCreate = async () => {
    setFormError(null);
    setFormLoading(true);

    try {
      await adminApi.createUser({
        name: formName,
        email: formEmail,
        password: formPassword,
        role: formRole,
        actif: formActif,
      });

      setCreateDialogOpen(false);
      resetForm();
      loadUsers();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur lors de la création";
      setFormError(message);
    } finally {
      setFormLoading(false);
    }
  };

  // Update user
  const handleUpdate = async () => {
    if (!selectedUser) return;

    setFormError(null);
    setFormLoading(true);

    try {
      const updateData: { name?: string; email?: string; password?: string; role?: string; actif?: boolean } = {};

      if (formName !== selectedUser.name) updateData.name = formName;
      if (formEmail !== selectedUser.email) updateData.email = formEmail;
      if (formPassword) updateData.password = formPassword;
      if (formRole !== selectedUser.role) updateData.role = formRole;
      if (formActif !== selectedUser.actif) updateData.actif = formActif;

      await adminApi.updateUser(selectedUser.id, updateData);

      setEditDialogOpen(false);
      resetForm();
      setSelectedUser(null);
      loadUsers();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur lors de la mise à jour";
      setFormError(message);
    } finally {
      setFormLoading(false);
    }
  };

  // Delete user
  const handleDelete = async () => {
    if (!selectedUser) return;

    setFormLoading(true);

    try {
      await adminApi.deleteUser(selectedUser.id);
      setDeleteDialogOpen(false);
      setSelectedUser(null);
      loadUsers();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur lors de la suppression";
      setError(message);
    } finally {
      setFormLoading(false);
    }
  };

  // Role badge
  const RoleBadge = ({ role }: { role: string }) => {
    switch (role) {
      case "admin":
        return (
          <Badge variant="destructive" className="gap-1">
            <ShieldCheck className="h-3 w-3" />
            {t("roles.admin")}
          </Badge>
        );
      case "notaire":
        return (
          <Badge variant="default" className="gap-1">
            <Shield className="h-3 w-3" />
            {t("roles.notaire")}
          </Badge>
        );
      case "assistant":
        return (
          <Badge variant="secondary" className="gap-1">
            <Users className="h-3 w-3" />
            {t("roles.assistant")}
          </Badge>
        );
      default:
        return <Badge variant="outline">{role}</Badge>;
    }
  };

  // Status badge
  const StatusBadge = ({ actif }: { actif: boolean }) => {
    return actif ? (
      <Badge variant="outline" className="gap-1 text-green-600 border-green-600">
        <Check className="h-3 w-3" />
        {t("status.active")}
      </Badge>
    ) : (
      <Badge variant="outline" className="gap-1 text-red-600 border-red-600">
        <X className="h-3 w-3" />
        {t("status.inactive")}
      </Badge>
    );
  };

  if (!currentUser) {
    return (
      <AppShell noPadding>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell noPadding>
      <div className="flex flex-col h-full overflow-hidden">
        {/* Header - fixed 65px */}
        <div className="px-4 border-b bg-background flex items-center justify-between shrink-0 h-[65px]">
          <h2 className="text-xl font-bold">{t("users.title")}</h2>
        </div>

        {/* Scrollable content */}
        <div className="px-6 py-2 space-y-4 flex-1 min-h-0 overflow-y-auto">
          {/* Error alert */}
          {error && (
            <div className="border border-destructive rounded-md p-3">
              <div className="flex items-center gap-2 text-destructive text-sm">
                <AlertCircle className="h-4 w-4" />
                <p>{error}</p>
              </div>
            </div>
          )}

          {/* Users section */}
          <div className="space-y-2">
            {/* Section header */}
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-base flex items-center gap-2">
                <Users className="h-4 w-4" />
                {t("users.list")} ({total})
              </h3>
              <div className="flex items-center gap-2">
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder={t("users.search")}
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9 h-8 text-sm"
                  />
                </div>
                <Button size="sm" onClick={openCreateDialog} className="gap-1">
                  <UserPlus className="h-3 w-3" />
                  {t("users.addUser")}
                </Button>
              </div>
            </div>

            {/* Users table */}
            <div className="border rounded-md">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : filteredUsers.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <p className="text-sm text-muted-foreground">
                    {searchTerm ? t("users.noResults") : t("users.noUsers")}
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-sm">{t("users.columns.name")}</TableHead>
                      <TableHead className="text-sm">{t("users.columns.email")}</TableHead>
                      <TableHead className="text-sm">{t("users.columns.role")}</TableHead>
                      <TableHead className="text-sm">{t("users.columns.status")}</TableHead>
                      <TableHead className="text-sm">{t("users.columns.createdAt")}</TableHead>
                      <TableHead className="text-right text-sm">{t("users.columns.actions")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredUsers.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium text-sm">{user.name}</TableCell>
                        <TableCell className="text-sm">{user.email}</TableCell>
                        <TableCell>
                          <RoleBadge role={user.role} />
                        </TableCell>
                        <TableCell>
                          <StatusBadge actif={user.actif} />
                        </TableCell>
                        <TableCell className="text-sm">
                          {user.created_at
                            ? new Date(user.created_at).toISOString().split("T")[0]
                            : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => openEditDialog(user)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => openDeleteDialog(user)}
                              disabled={user.id === currentUser?.id}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </div>
        </div>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t("users.createDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("users.createDialog.description")}
            </DialogDescription>
          </DialogHeader>

          {formError && (
            <div className="flex items-center gap-2 text-destructive text-sm">
              <AlertCircle className="h-4 w-4" />
              <p>{formError}</p>
            </div>
          )}

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">{t("users.form.name")}</Label>
              <Input
                id="name"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder={t("users.form.namePlaceholder")}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="email">{t("users.form.email")}</Label>
              <Input
                id="email"
                type="email"
                value={formEmail}
                onChange={(e) => setFormEmail(e.target.value)}
                placeholder={t("users.form.emailPlaceholder")}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="password">{t("users.form.password")}</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={formPassword}
                  onChange={(e) => setFormPassword(e.target.value)}
                  placeholder={t("users.form.passwordPlaceholder")}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="role">{t("users.form.role")}</Label>
              <Select value={formRole} onValueChange={setFormRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="notaire">{t("roles.notaire")}</SelectItem>
                  <SelectItem value="assistant">{t("roles.assistant")}</SelectItem>
                  <SelectItem value="admin">{t("roles.admin")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="actif">{t("users.form.active")}</Label>
              <Switch
                id="actif"
                checked={formActif}
                onCheckedChange={setFormActif}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateDialogOpen(false)}
            >
              {t("users.form.cancel")}
            </Button>
            <Button onClick={handleCreate} disabled={formLoading}>
              {formLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("users.form.create")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t("users.editDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("users.editDialog.description")}
            </DialogDescription>
          </DialogHeader>

          {formError && (
            <div className="flex items-center gap-2 text-destructive text-sm">
              <AlertCircle className="h-4 w-4" />
              <p>{formError}</p>
            </div>
          )}

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-name">{t("users.form.name")}</Label>
              <Input
                id="edit-name"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="edit-email">{t("users.form.email")}</Label>
              <Input
                id="edit-email"
                type="email"
                value={formEmail}
                onChange={(e) => setFormEmail(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="edit-password">
                {t("users.form.newPassword")}
              </Label>
              <div className="relative">
                <Input
                  id="edit-password"
                  type={showPassword ? "text" : "password"}
                  value={formPassword}
                  onChange={(e) => setFormPassword(e.target.value)}
                  placeholder={t("users.form.newPasswordPlaceholder")}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="edit-role">{t("users.form.role")}</Label>
              <Select value={formRole} onValueChange={setFormRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="notaire">{t("roles.notaire")}</SelectItem>
                  <SelectItem value="assistant">{t("roles.assistant")}</SelectItem>
                  <SelectItem value="admin">{t("roles.admin")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="edit-actif">{t("users.form.active")}</Label>
              <Switch
                id="edit-actif"
                checked={formActif}
                onCheckedChange={setFormActif}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              {t("users.form.cancel")}
            </Button>
            <Button onClick={handleUpdate} disabled={formLoading}>
              {formLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("users.form.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("users.deleteDialog.title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("users.deleteDialog.description", {
                name: selectedUser?.name || "",
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("users.form.cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {formLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("users.form.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      </div>
    </AppShell>
  );
}
