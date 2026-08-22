(function exposeTreemapData(root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.SILARASTreemap = api;
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  function numericValue(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function compareGroups(left, right) {
    return right.value - left.value || left.name.localeCompare(right.name, "id", { numeric: true });
  }

  function compareGroupsAscending(left, right) {
    return left.value - right.value || left.name.localeCompare(right.name, "id", { numeric: true });
  }

  function orderForDisplay(groups, sortOrder) {
    if (sortOrder !== "asc") return groups;

    const remainder = groups.filter((group) => group.isRemainder);
    const visible = groups
      .filter((group) => !group.isRemainder)
      .map((group) => {
        const childRemainder = group.children.filter((child) => child.isRemainder);
        const children = group.children
          .filter((child) => !child.isRemainder)
          .sort(compareGroupsAscending);
        return { ...group, children: [...children, ...childRemainder] };
      })
      .sort(compareGroupsAscending);

    return [...visible, ...remainder];
  }

  function buildTreemapData(records, options = {}) {
    const {
      topKey,
      childKey,
      metricKey,
      maxGroups = 10,
      maxChildren = 8,
      sortOrder = "desc",
    } = options;
    if (!Array.isArray(records) || !topKey || !childKey || !metricKey) return [];

    const groupMap = new Map();
    records.forEach((record) => {
      if (!record || typeof record !== "object") return;
      const top = String(record[topKey] ?? "—");
      const child = String(record[childKey] ?? "—");
      const value = numericValue(record[metricKey]);
      if (!groupMap.has(top)) groupMap.set(top, new Map());
      const childMap = groupMap.get(top);
      childMap.set(child, (childMap.get(child) || 0) + value);
    });

    const groups = Array.from(groupMap.entries())
      .map(([name, childMap]) => {
        const children = Array.from(childMap.entries())
          .map(([childName, value]) => ({ name: childName, value }))
          .sort(compareGroups);
        const value = children.reduce((total, child) => total + child.value, 0);
        const childLimit = Math.max(1, Number(maxChildren) || 8);
        if (children.length > childLimit) {
          const visibleChildren = children.slice(0, childLimit);
          const remainder = children.slice(childLimit).reduce((total, child) => total + child.value, 0);
          visibleChildren.push({ name: "Kegiatan lainnya", value: remainder, isRemainder: true });
          return { name, value, children: visibleChildren };
        }
        return { name, value, children };
      })
      .sort(compareGroups);

    const groupLimit = Math.max(1, Number(maxGroups) || 10);
    const visibleGroups = groups.slice(0, groupLimit);
    const remainder = groups.slice(groupLimit);
    if (remainder.length) {
      visibleGroups.push({
        name: "Lainnya",
        value: remainder.reduce((total, group) => total + group.value, 0),
        children: [],
        isRemainder: true,
      });
    }
    return orderForDisplay(visibleGroups, sortOrder);
  }

  return Object.freeze({ buildTreemapData });
});
