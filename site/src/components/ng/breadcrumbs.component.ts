import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import {
  VoltBreadcrumbItem, VoltBreadcrumbLink, VoltBreadcrumbList, VoltBreadcrumbPage, VoltBreadcrumbs,
  VoltBreadcrumbSeparator,
} from "@voltui/components";

export interface Crumb { label: string; href?: string }

@Component({
  selector: "app-breadcrumbs",
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [VoltBreadcrumbs, VoltBreadcrumbList, VoltBreadcrumbItem, VoltBreadcrumbLink, VoltBreadcrumbPage, VoltBreadcrumbSeparator],
  template: `
    <volt-breadcrumbs>
      <volt-breadcrumb-list>
        @for (c of items(); track $index; let last = $last) {
          <volt-breadcrumb-item>
            @if (c.href && !last) {
              <volt-breadcrumb-link [href]="c.href">{{ c.label }}</volt-breadcrumb-link>
            } @else {
              <volt-breadcrumb-page>{{ c.label }}</volt-breadcrumb-page>
            }
          </volt-breadcrumb-item>
          @if (!last) { <volt-breadcrumb-separator /> }
        }
      </volt-breadcrumb-list>
    </volt-breadcrumbs>
  `,
})
export class BreadcrumbsComponent {
  readonly items = input<Crumb[]>([]);
}
