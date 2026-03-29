import {
  Document,
  NodeIO,
} from "@gltf-transform/core";

// ─── Color palette ──────────────────────────────────────────────────
const PALETTE = {
  armor:     [0.76, 0.68, 0.55, 1.0],
  armorDark: [0.40, 0.38, 0.32, 1.0],
  visor:     [0.15, 0.18, 0.22, 1.0],
  accent:    [0.72, 0.22, 0.18, 1.0],
  belt:      [0.12, 0.12, 0.12, 1.0],
  sole:      [0.30, 0.28, 0.24, 1.0],
  skin:      [0.55, 0.48, 0.40, 1.0],
};

// ─── Bone definitions ───────────────────────────────────────────────
// [name, parentIdx, [tx,ty,tz], shape, [dims], colorKey]
const BONES = [
  ["root",           -1, [0,    0,     0],       "box",       [0.01, 0.01, 0.01],        "armor"],
  ["hips",            0, [0,    0.98,  0],       "trapezoid", [0.32, 0.14, 0.18, 0.26],  "belt"],
  ["spine",           1, [0,    0.10,  0],       "trapezoid", [0.26, 0.18, 0.16, 0.30],  "skin"],
  ["chest",           2, [0,    0.18,  0],       "trapezoid", [0.34, 0.22, 0.20, 0.28],  "armor"],
  ["neck",            3, [0,    0.14,  0],       "cylinder",  [0.05, 0.08, 12],           "skin"],
  ["head",            4, [0,    0.08,  0],       "helmet",    [0.11, 0.14, 0.13],         "armorDark"],
  ["clavicleL",       3, [0.17, 0.12,  0],       "box",       [0.10, 0.08, 0.10],         "armor"],
  ["upperArmL",       6, [0.12, 0,     0],       "cylinder",  [0.050, 0.26, 10],          "armor"],
  ["lowerArmL",       7, [0.28, 0,     0],       "cylinder",  [0.042, 0.24, 10],          "armorDark"],
  ["handL",           8, [0.26, 0,     0],       "box",       [0.10, 0.04, 0.08],         "skin"],
  ["clavicleR",       3, [-0.17, 0.12, 0],       "box",       [0.10, 0.08, 0.10],         "armor"],
  ["upperArmR",      10, [-0.12, 0,    0],       "cylinder",  [0.050, 0.26, 10],          "armor"],
  ["lowerArmR",      11, [-0.28, 0,    0],       "cylinder",  [0.042, 0.24, 10],          "armorDark"],
  ["handR",          12, [-0.26, 0,    0],       "box",       [0.10, 0.04, 0.08],         "skin"],
  ["upperLegL",       1, [0.10, -0.06, 0],       "cylinder",  [0.065, 0.40, 10],          "armor"],
  ["lowerLegL",      14, [0,    -0.42, 0],       "cylinder",  [0.055, 0.38, 10],          "armorDark"],
  ["footL",          15, [0,    -0.40, 0.04],    "box",       [0.10, 0.08, 0.24],         "sole"],
  ["toeL",           16, [0,     0,    0.12],    "box",       [0.08, 0.05, 0.08],         "sole"],
  ["upperLegR",       1, [-0.10, -0.06, 0],      "cylinder",  [0.065, 0.40, 10],          "armor"],
  ["lowerLegR",      18, [0,     -0.42, 0],      "cylinder",  [0.055, 0.38, 10],          "armorDark"],
  ["footR",          19, [0,     -0.40, 0.04],   "box",       [0.10, 0.08, 0.24],         "sole"],
  ["toeR",           20, [0,      0,    0.12],   "box",       [0.08, 0.05, 0.08],         "sole"],
  // Armor detail pieces (extra bones for visual only)
  ["shoulderPadL",    7, [0.04,  0.06,  0],      "box",       [0.14, 0.05, 0.14],         "armor"],
  ["shoulderPadR",   11, [-0.04, 0.06,  0],      "box",       [0.14, 0.05, 0.14],         "armor"],
  ["chestPlate",      3, [0,     0.04,  0.10],   "box",       [0.22, 0.16, 0.04],         "armorDark"],
  ["beltFront",       1, [0,     0.02,  0.10],   "box",       [0.20, 0.06, 0.04],         "belt"],
  ["pouchL",          1, [0.14,  0.00,  0.06],   "box",       [0.06, 0.08, 0.06],         "armorDark"],
  ["pouchR",          1, [-0.14, 0.00,  0.06],   "box",       [0.06, 0.08, 0.06],         "armorDark"],
  ["kneePadL",       15, [0,     0.10,  0.05],   "box",       [0.08, 0.10, 0.04],         "armor"],
  ["kneePadR",       19, [0,     0.10,  0.05],   "box",       [0.08, 0.10, 0.04],         "armor"],
  ["visor",           5, [0,    -0.01,  0.08],   "box",       [0.16, 0.06, 0.04],         "visor"],
  ["helmetCrest",     5, [0,     0.10, -0.02],   "box",       [0.04, 0.04, 0.16],         "accent"],
];

// ─── Geometry generators ────────────────────────────────────────────

function makeBox(sx, sy, sz) {
  const hx=sx/2, hy=sy/2, hz=sz/2;
  const c=[[-hx,-hy,-hz],[hx,-hy,-hz],[hx,hy,-hz],[-hx,hy,-hz],
           [-hx,-hy,hz],[hx,-hy,hz],[hx,hy,hz],[-hx,hy,hz]];
  const faces=[[[1,0,3,2],[0,0,-1]],[[4,5,6,7],[0,0,1]],[[0,4,7,3],[-1,0,0]],
               [[5,1,2,6],[1,0,0]],[[3,7,6,2],[0,1,0]],[[0,1,5,4],[0,-1,0]]];
  const pos=[],norm=[],idx=[];
  for(const[v,n]of faces){const b=pos.length/3;for(const vi of v){pos.push(...c[vi]);norm.push(...n);}idx.push(b,b+1,b+2,b,b+2,b+3);}
  return{positions:new Float32Array(pos),normals:new Float32Array(norm),indices:new Uint16Array(idx)};
}

function makeTrapezoid(topW,h,depth,bottomW) {
  const htw=topW/2,hbw=bottomW/2,hh=h/2,hd=depth/2;
  const c=[[-hbw,-hh,-hd],[hbw,-hh,-hd],[hbw,-hh,hd],[-hbw,-hh,hd],
           [-htw,hh,-hd],[htw,hh,-hd],[htw,hh,hd],[-htw,hh,hd]];
  const faces=[[[0,1,5,4],[0,0,-1]],[[2,3,7,6],[0,0,1]],[[3,0,4,7],[-1,0,0]],
               [[1,2,6,5],[1,0,0]],[[4,5,6,7],[0,1,0]],[[3,2,1,0],[0,-1,0]]];
  const pos=[],norm=[],idx=[];
  for(const[v,n]of faces){const b=pos.length/3;for(const vi of v){pos.push(...c[vi]);norm.push(...n);}idx.push(b,b+1,b+2,b,b+2,b+3);}
  return{positions:new Float32Array(pos),normals:new Float32Array(norm),indices:new Uint16Array(idx)};
}

function makeCylinder(radius,height,segments) {
  const pos=[],norm=[],idx=[];
  const hy=height/2, seg=segments||10;
  for(let i=0;i<seg;i++){
    const a0=(i/seg)*Math.PI*2, a1=((i+1)/seg)*Math.PI*2;
    const c0=Math.cos(a0),s0=Math.sin(a0),c1=Math.cos(a1),s1=Math.sin(a1);
    const b=pos.length/3;
    pos.push(c0*radius,-hy,s0*radius, c1*radius,-hy,s1*radius, c1*radius,hy,s1*radius, c0*radius,hy,s0*radius);
    norm.push(c0,0,s0, c1,0,s1, c1,0,s1, c0,0,s0);
    idx.push(b,b+1,b+2, b,b+2,b+3);
  }
  // caps
  for(const[sign,ny]of[[ 1,1],[-1,-1]]){
    const ctr=pos.length/3;
    pos.push(0,sign*hy,0); norm.push(0,ny,0);
    for(let i=0;i<seg;i++){const a=(i/seg)*Math.PI*2;pos.push(Math.cos(a)*radius,sign*hy,Math.sin(a)*radius);norm.push(0,ny,0);}
    for(let i=0;i<seg;i++){
      if(sign>0) idx.push(ctr,ctr+1+i,ctr+1+(i+1)%seg);
      else idx.push(ctr,ctr+1+(i+1)%seg,ctr+1+i);
    }
  }
  return{positions:new Float32Array(pos),normals:new Float32Array(norm),indices:new Uint16Array(idx)};
}

function makeHelmet(rx,ry,rz) {
  const lat=12,lon=16, pos=[],norm=[],idx=[];
  for(let i=0;i<=lat;i++){
    const t=(i/lat)*Math.PI, st=Math.sin(t), ct=Math.cos(t);
    for(let j=0;j<=lon;j++){
      const p=(j/lon)*Math.PI*2, nx=st*Math.cos(p), ny=ct, nz=st*Math.sin(p);
      pos.push(nx*rx,ny*ry,nz*rz); norm.push(nx,ny,nz);
    }
  }
  for(let i=0;i<lat;i++)for(let j=0;j<lon;j++){
    const a=i*(lon+1)+j, b=a+lon+1;
    idx.push(a,b,a+1, b,b+1,a+1);
  }
  return{positions:new Float32Array(pos),normals:new Float32Array(norm),indices:new Uint16Array(idx)};
}

function generateShape(shape,dims){
  switch(shape){
    case"box":return makeBox(dims[0],dims[1],dims[2]);
    case"trapezoid":return makeTrapezoid(dims[0],dims[1],dims[2],dims[3]);
    case"cylinder":return makeCylinder(dims[0],dims[1],dims[2]||10);
    case"helmet":return makeHelmet(dims[0],dims[1],dims[2]);
    default:return makeBox(dims[0],dims[1],dims[2]);
  }
}

function rotateGeomZ90(geom,sign){
  const p=geom.positions,n=geom.normals;
  for(let i=0;i<p.length;i+=3){
    const x=p[i],y=p[i+1]; p[i]=-y*sign; p[i+1]=x*sign;
    const nx=n[i],ny=n[i+1]; n[i]=-ny*sign; n[i+1]=nx*sign;
  }
}

// ─── World positions & IBM ──────────────────────────────────────────

function computeWorldPositions(){
  const w=new Array(BONES.length);
  for(let i=0;i<BONES.length;i++){
    const[,pi,l]=BONES[i];
    w[i]=pi<0?[...l]:[w[pi][0]+l[0],w[pi][1]+l[1],w[pi][2]+l[2]];
  }
  return w;
}

function ibm(wp){return new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,-wp[0],-wp[1],-wp[2],1]);}

// ─── Build GLB ──────────────────────────────────────────────────────

async function main(){
  const doc=new Document(), buffer=doc.createBuffer("buffer"), scene=doc.createScene("Scene");
  const wp=computeWorldPositions();
  const leftArms=new Set(["upperArmL","lowerArmL"]);
  const rightArms=new Set(["upperArmR","lowerArmR"]);

  // Nodes
  const nodes=BONES.map(([name,,local])=>{const n=doc.createNode(name);n.setTranslation(local);return n;});
  for(let i=0;i<BONES.length;i++){const pi=BONES[i][1];if(pi>=0)nodes[pi].addChild(nodes[i]);else scene.addChild(nodes[i]);}

  // Skin
  const skin=doc.createSkin("Armature");
  const ibmArr=new Float32Array(BONES.length*16);
  for(let i=0;i<BONES.length;i++) ibmArr.set(ibm(wp[i]),i*16);
  skin.setInverseBindMatrices(doc.createAccessor("IBM").setType("MAT4").setArray(ibmArr).setBuffer(buffer));
  for(const n of nodes) skin.addJoint(n);
  skin.setSkeleton(nodes[0]);

  // Materials
  const mats={};
  for(const[k,c]of Object.entries(PALETTE)){
    mats[k]=doc.createMaterial(k).setBaseColorFactor(c)
      .setRoughnessFactor(k==="visor"?0.2:0.75)
      .setMetallicFactor(k==="visor"?0.8:k==="armor"?0.3:0.1);
  }

  // Group geometry by material
  const groups={};
  for(const k of Object.keys(PALETTE)) groups[k]={p:[],n:[],i:[],j:[],w:[],vc:0};

  for(let i=0;i<BONES.length;i++){
    const[name,,,shape,dims,ck]=BONES[i];
    if(name==="root")continue;
    const geom=generateShape(shape,dims);
    if(leftArms.has(name)&&shape==="cylinder") rotateGeomZ90(geom,1);
    if(rightArms.has(name)&&shape==="cylinder") rotateGeomZ90(geom,-1);

    const g=groups[ck], vc=geom.positions.length/3, bv=g.vc;
    for(let v=0;v<vc;v++){
      g.p.push(geom.positions[v*3]+wp[i][0],geom.positions[v*3+1]+wp[i][1],geom.positions[v*3+2]+wp[i][2]);
      g.n.push(geom.normals[v*3],geom.normals[v*3+1],geom.normals[v*3+2]);
      g.j.push(i,0,0,0); g.w.push(1,0,0,0);
    }
    for(const ix of geom.indices) g.i.push(ix+bv);
    g.vc+=vc;
  }

  // Mesh
  const mesh=doc.createMesh("MannequinBody");
  let tv=0,tt=0;
  for(const[k,g]of Object.entries(groups)){
    if(!g.vc)continue;
    const prim=doc.createPrimitive()
      .setIndices(doc.createAccessor(`idx_${k}`).setType("SCALAR").setArray(new Uint16Array(g.i)).setBuffer(buffer))
      .setAttribute("POSITION",doc.createAccessor(`pos_${k}`).setType("VEC3").setArray(new Float32Array(g.p)).setBuffer(buffer))
      .setAttribute("NORMAL",doc.createAccessor(`nrm_${k}`).setType("VEC3").setArray(new Float32Array(g.n)).setBuffer(buffer))
      .setAttribute("JOINTS_0",doc.createAccessor(`jnt_${k}`).setType("VEC4").setArray(new Uint16Array(g.j)).setBuffer(buffer))
      .setAttribute("WEIGHTS_0",doc.createAccessor(`wgt_${k}`).setType("VEC4").setArray(new Float32Array(g.w)).setBuffer(buffer))
      .setMaterial(mats[k]);
    mesh.addPrimitive(prim);
    tv+=g.vc; tt+=g.i.length/3;
  }

  scene.addChild(doc.createNode("MannequinMesh").setMesh(mesh).setSkin(skin));

  await new NodeIO().write("/home/claude/mannequin.glb",doc);

  console.log(`✓ Enhanced mannequin GLB`);
  console.log(`  Bones:     ${BONES.length}`);
  console.log(`  Vertices:  ${tv}`);
  console.log(`  Triangles: ${tt}`);
  console.log(`  Materials: ${Object.values(groups).filter(g=>g.vc>0).length}`);
  console.log(`\nHierarchy:`);
  (function tree(i,ind){
    console.log(`${ind}${BONES[i][0]} [${BONES[i][3]}] (${BONES[i][5]})`);
    for(let c=0;c<BONES.length;c++) if(BONES[c][1]===i) tree(c,ind+"  ");
  })(0,"  ");
}

main().catch(e=>{console.error(e);process.exit(1);});
