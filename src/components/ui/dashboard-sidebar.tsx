import React, { useState } from "react"
import { ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"

export type NavItemData = {
  id: string
  title: string
  icon: React.ElementType
  badge?: number | string
  shortcut?: string
  disabled?: boolean
  disabledReason?: string
  children?: NavItemData[]
}

export type NavGroupData = {
  heading?: string
  items: NavItemData[]
}

function WorkspaceSwitcher({
  name,
  plan,
}: {
  name: string
  plan?: string
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg px-2 py-2 mb-4 select-none">
      <div className="w-8 h-8 rounded-[6px] bg-primary text-primary-foreground flex items-center justify-center font-semibold text-[13px] shadow-sm shrink-0">
        {name.charAt(0)}
      </div>
      <div className="flex flex-col overflow-hidden">
        <span className="text-[13px] font-medium leading-none mb-1 text-foreground truncate max-w-[150px]">
          {name}
        </span>
        {plan ? (
          <span className="text-[11px] text-muted-foreground leading-none">
            {plan}
          </span>
        ) : null}
      </div>
    </div>
  )
}

function NavItem({
  item,
  activeId,
  onSelect,
  level = 0,
}: {
  item: NavItemData
  activeId: string
  onSelect: (id: string) => void
  level?: number
}) {
  const isActive = activeId === item.id
  const hasChildren = !!item.children
  const [isOpen, setIsOpen] = useState(false)

  const handleClick = () => {
    if (item.disabled) return
    if (hasChildren) {
      setIsOpen(!isOpen)
    } else {
      onSelect(item.id)
    }
  }

  return (
    <div className="flex flex-col w-full">
      <div
        className={cn(
          "group flex items-center justify-between px-2.5 py-[7px] rounded-[6px] transition-all duration-200 select-none",
          item.disabled
            ? "text-muted-foreground/40 cursor-not-allowed"
            : "cursor-pointer",
          isActive
            ? "bg-black/5 dark:bg-white/10 text-foreground font-medium"
            : !item.disabled &&
                "text-muted-foreground hover:bg-black/5 dark:hover:bg-white/5 hover:text-foreground/90"
        )}
        style={{ paddingLeft: `${level * 12 + 10}px` }}
        onClick={handleClick}
        role="button"
        aria-disabled={item.disabled || undefined}
        aria-current={isActive ? "page" : undefined}
        title={item.disabled ? item.disabledReason : undefined}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <item.icon
            className={cn(
              "w-[16px] h-[16px] transition-colors shrink-0",
              isActive
                ? "text-foreground"
                : item.disabled
                  ? "text-muted-foreground/40"
                  : "text-muted-foreground/70 group-hover:text-foreground/70"
            )}
            strokeWidth={1.5}
          />
          <span className="text-[13px] tracking-wide truncate">
            {item.title}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {item.shortcut && (
            <kbd className="hidden group-hover:inline-flex items-center justify-center h-5 px-1.5 text-[10px] font-medium font-mono text-muted-foreground/60 bg-background/50 border border-border/50 rounded-[4px] shadow-xs">
              {item.shortcut}
            </kbd>
          )}
          {item.badge && (
            <span className="flex items-center justify-center min-w-[20px] h-5 px-1.5 text-[10px] font-medium rounded-full bg-primary/10 text-primary">
              {item.badge}
            </span>
          )}
          {hasChildren && (
            <ChevronRight
              className={cn(
                "w-3.5 h-3.5 text-muted-foreground/50 transition-transform duration-200",
                isOpen && "rotate-90"
              )}
              strokeWidth={2}
            />
          )}
        </div>
      </div>

      {hasChildren && (
        <div
          className={cn(
            "grid transition-[grid-template-rows,opacity] duration-300 ease-in-out",
            isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
          )}
        >
          <div className="overflow-hidden min-h-0 relative flex flex-col gap-0.5 mt-0.5">
            <div
              className="absolute top-0 bottom-0 border-l border-black/5 dark:border-white/5"
              style={{ left: `${level * 12 + 17.5}px` }}
            />
            {item.children!.map((child) => (
              <NavItem
                key={child.id}
                item={child}
                activeId={activeId}
                onSelect={onSelect}
                level={level + 1}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function SidebarNav({
  className,
  groups,
  bottomItems,
  activeId,
  onSelect,
  workspaceName,
  workspacePlan,
}: {
  className?: string
  groups: NavGroupData[]
  bottomItems?: NavItemData[]
  activeId: string
  onSelect: (id: string) => void
  workspaceName: string
  workspacePlan?: string
}) {
  return (
    <div
      className={cn(
        "flex flex-col w-[260px] h-full bg-card/50 border-r border-border/50 p-3 font-sans",
        className
      )}
    >
      <WorkspaceSwitcher name={workspaceName} plan={workspacePlan} />

      <div className="flex-1 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] flex flex-col gap-4 mt-2">
        {groups.map((group, idx) => (
          <div key={group.heading ?? idx} className="flex flex-col gap-0.5">
            {group.heading && (
              <span className="px-2.5 mb-1 text-[11px] font-semibold tracking-wider text-muted-foreground/50 uppercase">
                {group.heading}
              </span>
            )}
            {group.items.map((item) => (
              <NavItem
                key={item.id}
                item={item}
                activeId={activeId}
                onSelect={onSelect}
              />
            ))}
          </div>
        ))}
      </div>

      {bottomItems && bottomItems.length > 0 && (
        <div className="mt-auto pt-4 border-t border-border/50 flex flex-col gap-0.5">
          {bottomItems.map((item) => (
            <NavItem
              key={item.id}
              item={item}
              activeId={activeId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}
