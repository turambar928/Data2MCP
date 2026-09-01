import React, { useState } from "react";
import { FieldSchema, TargetSchemaMap } from "./schema";

export function SchemaFormRenderer({
  schema,
  value,
  onChange,
  level = 0,
  label,
  filterText,
}: {
  schema: FieldSchema;
  value: any;
  onChange: (v: any) => void;
  level?: number;
  label?: string;
  filterText?: string;
}) {
  const indent = level * 12;
  const labelText = getLabelText(schema, label);

  if (filterText && !schemaMatches(schema, filterText, label)) {
    return null;
  }

  // --- primitive ---
  if (schema.kind === "string" || schema.kind === "number" || schema.kind === "boolean") {
    const val = value ?? schema.default ?? (schema.kind === "boolean" ? false : "");
    return (
      <div className="flex items-start gap-2 my-2" style={{ marginLeft: indent }}>
        <div className="w-56 text-xs text-gray-300">
          <div className="font-medium text-gray-100">{labelText}</div>
          {schema.description && (
            <div className="text-[11px] text-gray-500">{schema.description}</div>
          )}
        </div>
        <FieldInput schema={schema} value={val} onChange={onChange} />
      </div>
    );
  }

  // --- array ---
  if (schema.kind === "array") {
    return (
      <ArrayField
        schema={schema}
        value={value}
        onChange={onChange}
        level={level}
        label={label}
        filterText={filterText}
      />
    );
  }

  // --- object ---
  if (schema.kind === "object") {
    return (
      <ObjectField
        schema={schema}
        value={value}
        onChange={onChange}
        level={level}
        label={label}
        filterText={filterText}
      />
    );
  }

  return null;
}

function ArrayField({
  schema,
  value,
  onChange,
  level,
  label,
  filterText,
}: {
  schema: Extract<FieldSchema, { kind: "array" }>;
  value: any;
  onChange: (v: any) => void;
  level: number;
  label?: string;
  filterText?: string;
}) {
  const indent = level * 12;
  const labelText = getLabelText(schema, label);
  const arr = Array.isArray(value) ? value : schema.default ?? [];
  const [open, setOpen] = useState(true);
  const targetOptions =
    schema.item.kind === "object" ? schema.item.targetEnum ?? [] : [];
  const [newTarget, setNewTarget] = useState(
    targetOptions[0] ?? (schema.item.kind === "object" ? schema.item.defaultTarget ?? "" : "")
  );

  const addItem = () => {
    let itemSchema = schema.item;
    if (schema.item.kind === "object") {
      const target = newTarget || schema.item.defaultTarget;
      if (target && TargetSchemaMap[target]) itemSchema = TargetSchemaMap[target];
    }
    const defItem = defaultValueFor(itemSchema);
    if (schema.item.kind === "object" && newTarget) {
      defItem._target_ = newTarget;
    }
    onChange([...arr, defItem]);
  };

  const removeItem = (i: number) => {
    const next = arr.slice();
    next.splice(i, 1);
    onChange(next);
  };

  const duplicateItem = (i: number) => {
    const next = arr.slice();
    next.splice(i + 1, 0, arr[i]);
    onChange(next);
  };

  return (
    <div className="my-2" style={{ marginLeft: indent }}>
      <div className="flex items-center gap-2 text-xs bg-gray-800 rounded px-2 py-1">
        <button
          onClick={() => setOpen((v) => !v)}
          className="text-gray-300 hover:text-white"
          title={open ? "Collapse" : "Expand"}
        >
          {open ? "▾" : "▸"}
        </button>
        <span className="text-gray-200 font-medium">{labelText}</span>
        <span className="text-gray-500">({arr.length})</span>
        {schema.description && (
          <span className="text-[11px] text-gray-500">{schema.description}</span>
        )}
        {targetOptions.length > 0 && (
          <select
            className="ml-auto bg-gray-950 border border-gray-700 rounded text-[11px] px-2 py-0.5"
            value={newTarget}
            onChange={(e) => setNewTarget(e.target.value)}
            title="Select agent type"
          >
            {targetOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt.split(".").slice(-1)[0]}
              </option>
            ))}
          </select>
        )}
        <button
          onClick={addItem}
          className={`${targetOptions.length ? "" : "ml-auto "}text-[11px] bg-gray-700 hover:bg-gray-600 px-2 py-0.5 rounded`}
        >
          + add
        </button>
      </div>

      {open && (
        <div className="mt-2 space-y-2">
        {arr.map((item, i) => {
          // 关键：如果 item 是 object 且有 _target_，按 _target_ 选 schema
          let itemSchema = schema.item;
          let itemTarget = item?._target_;
          if (schema.item.kind === "object") {
            itemTarget = itemTarget ?? schema.item.defaultTarget;
            if (itemTarget && TargetSchemaMap[itemTarget]) itemSchema = TargetSchemaMap[itemTarget];
            if (itemTarget && !item?._target_) {
              item = { ...item, _target_: itemTarget };
            }
          }
          const itemTargets =
            schema.item.kind === "object" ? schema.item.targetEnum ?? [] : [];
          const currentItemTarget = itemTarget ?? itemTargets[0];

          return (
            <div key={i} className="border border-gray-800 rounded p-2 bg-gray-950">
              <div className="flex items-center mb-1">
                <div className="text-xs text-gray-500">#{i}</div>
                {itemTargets.length > 0 && (
                  <select
                    className="ml-2 bg-gray-900 border border-gray-700 rounded text-[11px] px-2 py-0.5"
                    value={currentItemTarget}
                    onChange={(e) => {
                      const nextTarget = e.target.value;
                      const nextSchema = TargetSchemaMap[nextTarget] ?? itemSchema;
                      const nextItem = defaultValueFor(nextSchema);
                      nextItem._target_ = nextTarget;
                      const next = arr.slice();
                      next[i] = nextItem;
                      onChange(next);
                    }}
                    title="Change item type"
                  >
                    {itemTargets.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt.split(".").slice(-1)[0]}
                      </option>
                    ))}
                  </select>
                )}
                <button
                  onClick={() => duplicateItem(i)}
                  className="ml-auto text-xs text-blue-300 hover:text-blue-200"
                >
                  复制
                </button>
                <button
                  onClick={() => removeItem(i)}
                  className="ml-3 text-xs text-red-400 hover:text-red-300"
                >
                  删除
                </button>
              </div>

              <SchemaFormRenderer
                schema={itemSchema}
                value={item}
                onChange={(v) => {
                  const next = arr.slice();
                  next[i] = v;
                  onChange(next);
                }}
                level={level + 1}
                filterText={filterText}
              />
            </div>
          );
        })}
        </div>
      )}
    </div>
  );
}

function ObjectField({
  schema,
  value,
  onChange,
  level,
  label,
  filterText,
}: {
  schema: Extract<FieldSchema, { kind: "object" }>;
  value: any;
  onChange: (v: any) => void;
  level: number;
  label?: string;
  filterText?: string;
}) {
  const indent = level * 12;
  const labelText = getLabelText(schema, label);
  let obj = value && typeof value === "object" ? value : {};
  // 自动补 _target_
  if (schema.targetRequired) {
    const target = obj._target_ ?? schema.defaultTarget;
    if (target) obj = { ...obj, _target_: target };
  }

  const [open, setOpen] = useState(true);
  const targetOptions = schema.targetEnum ?? (schema.defaultTarget ? [schema.defaultTarget] : []);
  const currentTarget = obj._target_ ?? schema.defaultTarget;
  const targetSchema = currentTarget && TargetSchemaMap[currentTarget]
    ? TargetSchemaMap[currentTarget]
    : schema;
  const fields = targetSchema.fields ?? {};
  const filteredFields = Object.entries(fields).filter(([k, fs]) => {
    if (schema.targetRequired && k === "_target_") return false;
    return filterText ? schemaMatches(fs, filterText, k) : true;
  });

  if (filterText && filteredFields.length === 0 && !schemaMatches(schema, filterText, label)) {
    return null;
  }

  return (
    <div className="my-2" style={{ marginLeft: indent }}>
      <div className="flex items-center gap-2 text-xs font-semibold text-gray-100 mb-2">
        <button
          onClick={() => setOpen((v) => !v)}
          className="text-gray-300 hover:text-white"
          title={open ? "Collapse" : "Expand"}
        >
          {open ? "▾" : "▸"}
        </button>
        <div>
          <div className="font-semibold">{labelText}</div>
          {schema.description && (
            <div className="text-[11px] font-normal text-gray-500">
              {schema.description}
            </div>
          )}
        </div>
        {schema.targetRequired && targetOptions.length > 0 && (
          <select
            className="ml-auto bg-gray-950 border border-gray-700 rounded text-[11px] px-2 py-0.5 font-normal"
            value={currentTarget}
            onChange={(e) => {
              const nextTarget = e.target.value;
              const nextSchema = TargetSchemaMap[nextTarget] ?? schema;
              const nextObj = defaultValueFor(nextSchema);
              onChange({ ...nextObj, _target_: nextTarget });
            }}
            title="_target_"
          >
            {targetOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt.split(".").slice(-1)[0]}
              </option>
            ))}
          </select>
        )}
      </div>

      {open && (
        <div className="space-y-1">
        {filteredFields.map(([k, fs]) => {
          // agent_configs 的 item schema 需要动态选，这里跳过空 fields 的 壳
          if ((fs as any).kind === "object" && (fs as any).fields && Object.keys((fs as any).fields).length === 0) {
            return null;
          }

          return (
            <SchemaFormRenderer
              key={k}
              schema={fs}
              value={obj[k]}
              label={k}
              level={level + 1}
              onChange={(v) => onChange({ ...obj, [k]: v })}
              filterText={filterText}
            />
          );
        })}
        </div>
      )}
    </div>
  );
}

function FieldInput({
  schema,
  value,
  onChange,
}: {
  schema: Extract<FieldSchema, { kind: "string" | "number" | "boolean" }>;
  value: any;
  onChange: (v: any) => void;
}) {
  if (schema.kind === "boolean") {
    return (
      <button
        type="button"
        className={`px-3 py-1 rounded text-xs border ${value ? "bg-green-700 border-green-500 text-green-100" : "bg-gray-900 border-gray-700 text-gray-300"}`}
        onClick={() => onChange(!value)}
      >
        {value ? "true" : "false"}
      </button>
    );
  }

  if (schema.enum?.length) {
    return (
      <select
        className="bg-gray-950 border border-gray-700 rounded text-xs px-2 py-1 flex-1"
        value={String(value)}
        onChange={(e) => onChange(cast(e.target.value, schema.kind))}
      >
        {schema.enum.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  }

  // secret 字段脱敏显示
  if (schema.secret) {
    return (
      <input
        className="bg-gray-950 border border-gray-700 rounded text-xs px-2 py-1 flex-1"
        type="password"
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
        placeholder="***"
      />
    );
  }

  return (
    <input
      className="bg-gray-950 border border-gray-700 rounded text-xs px-2 py-1 flex-1"
      type={schema.kind === "number" ? "number" : "text"}
      value={String(value ?? "")}
      onChange={(e) => onChange(cast(e.target.value, schema.kind))}
    />
  );
}

function cast(raw: string, kind: "string" | "number") {
  if (kind === "number") {
    const n = Number(raw);
    return Number.isFinite(n) ? n : 0;
  }
  return raw;
}

function defaultValueFor(schema: FieldSchema): any {
  if (schema.kind === "string") return schema.default ?? "";
  if (schema.kind === "number") return schema.default ?? 0;
  if (schema.kind === "boolean") return schema.default ?? false;
  if (schema.kind === "array") return schema.default ?? [];
  if (schema.kind === "object") {
    const obj: any = {};
    if (schema.targetRequired && schema.defaultTarget) {
      obj._target_ = schema.defaultTarget;
    }
    for (const [k, fs] of Object.entries(schema.fields ?? {})) {
      obj[k] = defaultValueFor(fs);
    }
    return obj;
  }
  return null;
}

function getLabelText(schema: FieldSchema, label?: string) {
  if (!label) return schema.title;
  if (label === schema.title) return label;
  return `${schema.title} (${label})`;
}

function schemaMatches(schema: FieldSchema, rawFilter: string, label?: string): boolean {
  const filter = rawFilter.trim().toLowerCase();
  if (!filter) return true;
  const haystack = [
    schema.title,
    label ?? "",
    schema.description ?? "",
  ]
    .join(" ")
    .toLowerCase();
  if (haystack.includes(filter)) return true;
  if (schema.kind === "object") {
    const fieldMatch = Object.entries(schema.fields ?? {}).some(([k, fs]) => schemaMatches(fs, filter, k));
    if (fieldMatch) return true;
    if (schema.targetEnum?.length) {
      return schema.targetEnum.some((target) => {
        const targetSchema = TargetSchemaMap[target];
        return targetSchema ? schemaMatches(targetSchema, filter, target) : false;
      });
    }
    return false;
  }
  if (schema.kind === "array") {
    if (schema.item.kind === "object" && schema.item.targetEnum?.length) {
      return schema.item.targetEnum.some((target) => {
        const targetSchema = TargetSchemaMap[target];
        return targetSchema ? schemaMatches(targetSchema, filter, target) : false;
      });
    }
    return schemaMatches(schema.item, filter, schema.item.title);
  }
  return false;
}
